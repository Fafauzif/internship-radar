from __future__ import annotations

from dataclasses import replace

from .models import RawOpportunity
from .text_utils import build_opportunity_id, normalize_url


def _unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(x for x in items if x))


def _prefer(a: str, b: str) -> str:
    # Prefer non-empty; if both exist, prefer the longer text for descriptions and richer fields.
    if not a:
        return b
    if not b:
        return a
    return b if len(b) > len(a) else a


def merge_pair(a: RawOpportunity, b: RawOpportunity) -> RawOpportunity:
    merged = replace(a)
    merged.sources = _unique(a.sources + b.sources)
    merged.source_job_ids = _unique(a.source_job_ids + b.source_job_ids)
    merged.source_urls = _unique(a.source_urls + b.source_urls)
    for field_name in (
        "application_url", "canonical_url", "company", "title", "location", "city", "country",
        "posted_at", "deadline", "start_date", "duration", "compensation_min", "compensation_max",
        "compensation_currency", "compensation_period", "description",
    ):
        setattr(merged, field_name, _prefer(getattr(a, field_name), getattr(b, field_name)))
    if merged.remote_type == "UNKNOWN" and b.remote_type != "UNKNOWN":
        merged.remote_type = b.remote_type
    if merged.employment_type == "UNKNOWN" and b.employment_type != "UNKNOWN":
        merged.employment_type = b.employment_type
    if merged.compensation_status == "UNKNOWN" and b.compensation_status != "UNKNOWN":
        merged.compensation_status = b.compensation_status
    merged.discovered_query = " | ".join(_unique((a.discovered_query + " | " + b.discovered_query).split(" | ")))
    merged.last_seen = max(a.last_seen, b.last_seen)
    merged.first_seen = min(a.first_seen, b.first_seen)
    return merged


def recompute_identity(opp: RawOpportunity) -> RawOpportunity:
    source = opp.sources[0] if opp.sources else "UNKNOWN"
    source_job_id = opp.source_job_ids[0] if opp.source_job_ids else ""
    opp.canonical_url = normalize_url(opp.canonical_url or opp.application_url or (opp.source_urls[0] if opp.source_urls else ""))
    opp.opportunity_id, opp.dedupe_key = build_opportunity_id(
        opp.company, opp.title, opp.location, opp.canonical_url, source, source_job_id
    )
    return opp


def deduplicate(opportunities: list[RawOpportunity]) -> list[RawOpportunity]:
    by_key: dict[str, RawOpportunity] = {}
    url_to_key: dict[str, str] = {}
    for original in opportunities:
        opp = recompute_identity(original)
        candidate_keys = []
        # Loss-averse dedupe: exact canonical URL / identity are strong enough to merge.
        # A company+title+location dedupe_key is only used when no URL exists, because
        # recurring yearly internships can legitimately share those three fields.
        if opp.canonical_url:
            candidate_keys.append("u:" + opp.canonical_url)
        candidate_keys.append("i:" + opp.opportunity_id)
        if not opp.canonical_url and opp.dedupe_key:
            candidate_keys.append("d:" + opp.dedupe_key)

        existing_key = next((k for k in candidate_keys if k in by_key), None)
        if not existing_key and opp.canonical_url and opp.canonical_url in url_to_key:
            existing_key = url_to_key[opp.canonical_url]

        if existing_key:
            merged = merge_pair(by_key[existing_key], opp)
            merged = recompute_identity(merged)
            for key in list(by_key):
                if by_key[key] is by_key[existing_key]:
                    by_key[key] = merged
            for key in candidate_keys:
                by_key[key] = merged
            if merged.canonical_url:
                url_to_key[merged.canonical_url] = existing_key
        else:
            primary_key = candidate_keys[0]
            for key in candidate_keys:
                by_key[key] = opp
            if opp.canonical_url:
                url_to_key[opp.canonical_url] = primary_key

    unique_by_id: dict[str, RawOpportunity] = {}
    for opp in by_key.values():
        unique_by_id[opp.opportunity_id] = opp
    return list(unique_by_id.values())
