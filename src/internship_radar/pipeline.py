from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from .clients.exa import ExaClient
from .clients.gemini import GeminiClient
from .clients.jsearch import JSearchClient
from .clients.webhook import AppsScriptWebhookClient, UsageSnapshot
from .dedupe import deduplicate, recompute_identity
from .eligibility import evaluate_eligibility
from .filtering import is_candidate_for_ai
from .models import RadarRecord, RawOpportunity, RunStats
from .normalize import normalize_exa, normalize_jsearch
from .planner import plan_queries
from .scoring import action_priority, career_fit_score, fit_band, priority_bucket, summary_reason

log = logging.getLogger(__name__)


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _budget_available(settings: dict[str, Any], usage: UsageSnapshot) -> tuple[int, int]:
    b = settings["budgets"]
    j_remaining = max(0, int(b["jsearch_monthly_cap"]) - usage.jsearch_requests)
    exa_budget_remaining = max(0.0, float(b["exa_monthly_budget_usd"]) - usage.exa_cost_usd)
    # Standard Exa search is configured as an estimate only; actual response cost is logged and authoritative.
    estimated_cost = float(b.get("exa_estimated_search_cost_usd", 0.007))
    e_remaining = int(exa_budget_remaining / estimated_cost) if estimated_cost > 0 else 0
    return j_remaining, e_remaining


def _enrich_from_ai(opp: RawOpportunity, ai: Any) -> None:
    if not opp.company and ai.employer_name:
        opp.company = ai.employer_name
    if ai.normalized_title and not opp.title:
        opp.title = ai.normalized_title
    if ai.work_mode != "UNKNOWN" and opp.remote_type == "UNKNOWN":
        opp.remote_type = ai.work_mode
    if ai.schedule_type != "UNKNOWN" and opp.employment_type == "UNKNOWN":
        opp.employment_type = ai.schedule_type
    if not opp.deadline and ai.deadline:
        opp.deadline = ai.deadline
    if not opp.start_date and ai.start_date:
        opp.start_date = ai.start_date
    if not opp.duration and ai.duration:
        opp.duration = ai.duration
    recompute_identity(opp)


def _to_radar(opp: RawOpportunity, ai: Any, profile: dict[str, Any]) -> RadarRecord:
    eligibility, eligibility_reason, timezone_compatibility = evaluate_eligibility(opp, ai, profile)
    fit, parts = career_fit_score(profile, opp, ai)
    if eligibility != "NOT_RECOMMENDED" and fit < int(profile.get("minimum_recommended_fit", 45)):
        eligibility = "NOT_RECOMMENDED"
        eligibility_reason = f"Career fit {fit}/100 is below the configured minimum."
    deadline = ai.deadline or opp.deadline
    priority = action_priority(fit, eligibility, ai)
    compensation = ai.compensation_text or ai.compensation_status
    return RadarRecord(
        opportunity_id=opp.opportunity_id,
        company=opp.company or ai.employer_name,
        title=ai.normalized_title or opp.title,
        category=ai.role_category,
        location=opp.location or ai.location_requirement,
        work_mode=ai.work_mode if ai.work_mode != "UNKNOWN" else opp.remote_type,
        schedule_type=ai.schedule_type,
        deadline=deadline,
        start_date=ai.start_date or opp.start_date,
        compensation=compensation,
        eligibility=eligibility,
        eligibility_reason=eligibility_reason,
        timezone_compatibility=timezone_compatibility,
        career_fit_score=fit,
        fit_band=fit_band(fit),
        action_priority=priority,
        priority_bucket=priority_bucket(eligibility, deadline, str(profile.get("timezone", "Asia/Jakarta"))),
        evaluation_confidence=ai.confidence,
        missing_critical_fields=" | ".join(ai.missing_critical_fields),
        required_skills=" | ".join(ai.required_skills),
        preferred_skills=" | ".join(ai.preferred_skills),
        summary_reason=summary_reason(ai, fit, parts, eligibility),
        application_url=opp.application_url or opp.canonical_url,
        evaluated_at=utcnow(),
    )


def run_pipeline(settings: dict[str, Any], profile: dict[str, Any], searches: dict[str, Any], mode: str = "scheduled") -> RunStats:
    run = RunStats(run_id=str(uuid.uuid4()), mode=mode, started_at=utcnow())
    errors: list[str] = []

    webhook = AppsScriptWebhookClient(os.environ["APPS_SCRIPT_WEBHOOK_URL"], os.environ["WEBHOOK_SECRET"])
    try:
        usage = webhook.usage_snapshot()
    except Exception as exc:
        # Failing closed protects the monthly budget. User can fix webhook rather than burn APIs blindly.
        raise RuntimeError(f"Could not read monthly usage from Apps Script; refusing to spend API budget: {exc}") from exc

    j_remaining, e_remaining = _budget_available(settings, usage)
    j_plan, e_plan = plan_queries(searches, settings, mode)
    j_plan = j_plan[:j_remaining]
    e_plan = e_plan[:e_remaining]

    opportunities: list[RawOpportunity] = []

    j_client = JSearchClient(os.environ["JSEARCH_API_KEY"])
    for item in j_plan:
        try:
            query = item["query"]
            run.jsearch_requests += 1
            jobs = j_client.search(query, country=item.get("country", "id"), date_posted=item.get("date_posted", "month"))
            opportunities.extend(normalize_jsearch(job, query) for job in jobs)
        except Exception as exc:
            errors.append(f"JSearch[{item.get('query','?')}]: {exc}")
            log.exception("JSearch query failed")

    e_client = ExaClient(os.environ["EXA_API_KEY"])
    exa_results_per_query = int(settings.get("pipeline", {}).get("exa_results_per_query", 10))
    for item in e_plan:
        try:
            query = item["query"]
            run.exa_requests += 1
            result = e_client.search(query, num_results=exa_results_per_query, user_location=item.get("user_location", "ID"))
            run.exa_cost_usd += result.cost_usd
            opportunities.extend(normalize_exa(row, query) for row in result.results)
        except Exception as exc:
            errors.append(f"Exa[{item.get('query','?')}]: {exc}")
            log.exception("Exa query failed")

    run.opportunities_discovered = len(opportunities)
    opportunities = deduplicate(opportunities)
    run.opportunities_after_dedupe = len(opportunities)

    candidates = [opp for opp in opportunities if is_candidate_for_ai(opp)]
    candidates = candidates[: int(settings["budgets"]["gemini_max_per_run"])]
    gemini = GeminiClient(os.environ["GEMINI_API_KEY"], model=settings["gemini_model"])
    radar: list[RadarRecord] = []

    for opp in candidates:
        try:
            ai = gemini.extract(opp)
            run.gemini_calls += 1
            _enrich_from_ai(opp, ai)
            radar.append(_to_radar(opp, ai, profile))
        except Exception as exc:
            errors.append(f"Gemini[{opp.title[:60]}]: {exc}")
            log.exception("Gemini extraction failed")

    # AI enrichment can improve company/title metadata, allowing a second stronger dedupe pass.
    opportunities = deduplicate(opportunities)
    by_id = {x.opportunity_id: x for x in opportunities}
    radar = [r for r in radar if r.opportunity_id in by_id]
    radar_by_id = {r.opportunity_id: r for r in radar}
    radar = list(radar_by_id.values())
    run.opportunities_after_dedupe = len(opportunities)
    run.opportunities_evaluated = len(radar)

    run.status = "PARTIAL_SUCCESS" if errors else "SUCCESS"
    if not opportunities and errors:
        run.status = "FAILED"
    run.error_summary = " || ".join(errors)[:10000]
    run.completed_at = utcnow()

    payload = {
        "action": "sync",
        "raw_opportunities": [x.to_dict() for x in opportunities],
        "radar": [x.to_dict() for x in radar],
        "run": run.to_dict(),
        "notify": bool(settings.get("notifications", {}).get("enabled", True)),
        "notification_min_fit": int(settings.get("notifications", {}).get("minimum_fit", 72)),
    }
    response = webhook.post(payload, timeout=90)
    sync = response.get("sync", {})
    run.raw_inserted = int(sync.get("raw_inserted", 0) or 0)
    run.raw_updated = int(sync.get("raw_updated", 0) or 0)
    run.radar_inserted = int(sync.get("radar_inserted", 0) or 0)
    run.radar_updated = int(sync.get("radar_updated", 0) or 0)
    return run
