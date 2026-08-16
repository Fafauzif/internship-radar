from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from .models import RawOpportunity
from .text_utils import build_opportunity_id, clean_text, normalize_url


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _salary_status(min_salary: Any, max_salary: Any, salary_text: Any) -> str:
    if min_salary is not None or max_salary is not None or clean_text(salary_text):
        return "PAID_DISCLOSED"
    return "UNKNOWN"


def normalize_jsearch(job: dict[str, Any], query: str) -> RawOpportunity:
    source_url = clean_text(job.get("job_google_link") or job.get("job_apply_link") or job.get("job_url"))
    apply_url = clean_text(job.get("job_apply_link") or source_url)
    canonical = normalize_url(apply_url or source_url)
    company = clean_text(job.get("employer_name"))
    title = clean_text(job.get("job_title"))
    location = clean_text(job.get("job_location"))
    city = clean_text(job.get("job_city"))
    country = clean_text(job.get("job_country"))
    remote = "REMOTE" if job.get("job_is_remote") is True else "UNKNOWN" if job.get("job_is_remote") is None else "ONSITE_OR_HYBRID"
    employment = clean_text(job.get("job_employment_type") or job.get("job_employment_types") or "UNKNOWN").upper()
    source_job_id = clean_text(job.get("job_id"))
    opportunity_id, dedupe_key = build_opportunity_id(company, title, location, canonical, "JSEARCH", source_job_id)
    now = _now_iso()
    min_salary = job.get("job_min_salary")
    max_salary = job.get("job_max_salary")
    return RawOpportunity(
        opportunity_id=opportunity_id,
        dedupe_key=dedupe_key,
        sources=["JSEARCH"],
        source_job_ids=[source_job_id] if source_job_id else [],
        source_urls=[source_url] if source_url else [],
        application_url=apply_url,
        canonical_url=canonical,
        discovered_query=query,
        company=company,
        title=title,
        location=location,
        city=city,
        country=country,
        remote_type=remote,
        employment_type=employment or "UNKNOWN",
        posted_at=clean_text(job.get("job_posted_at_datetime_utc") or job.get("job_posted_at")),
        deadline=clean_text(job.get("job_offer_expiration_datetime_utc") or job.get("job_offer_expiration_timestamp")),
        compensation_status=_salary_status(min_salary, max_salary, job.get("job_salary")),
        compensation_min="" if min_salary is None else str(min_salary),
        compensation_max="" if max_salary is None else str(max_salary),
        compensation_currency=clean_text(job.get("job_salary_currency")),
        compensation_period=clean_text(job.get("job_salary_period")),
        description=clean_text(job.get("job_description"), max_len=30000),
        first_seen=now,
        last_seen=now,
    )


def _guess_company_from_title(title: str) -> str:
    # Conservative only: common ATS/search result shapes such as "Role | Company".
    for sep in (" | ", " — ", " - ", " at "):
        parts = [p.strip() for p in title.split(sep) if p.strip()]
        if len(parts) == 2:
            left, right = parts
            intern_words = re.compile(r"\b(intern|internship|trainee|analyst|marketing|strategy|growth|communications?|business development|sustainability|esg)\b", re.I)
            if intern_words.search(left) and not intern_words.search(right):
                return right[:120]
            if intern_words.search(right) and not intern_words.search(left):
                return left[:120]
    return ""


def normalize_exa(result: dict[str, Any], query: str) -> RawOpportunity:
    url = clean_text(result.get("url") or result.get("id"))
    title = clean_text(result.get("title"))
    company = _guess_company_from_title(title)
    highlights = result.get("highlights") or []
    if isinstance(highlights, list):
        excerpt = "\n".join(clean_text(x) for x in highlights if x)
    else:
        excerpt = clean_text(highlights)
    description = clean_text(result.get("text") or excerpt or result.get("summary"), max_len=30000)
    source_job_id = clean_text(result.get("id"))
    canonical = normalize_url(url)
    opportunity_id, dedupe_key = build_opportunity_id(company, title, "", canonical, "EXA", source_job_id)
    now = _now_iso()
    return RawOpportunity(
        opportunity_id=opportunity_id,
        dedupe_key=dedupe_key,
        sources=["EXA"],
        source_job_ids=[source_job_id] if source_job_id else [],
        source_urls=[url] if url else [],
        application_url=url,
        canonical_url=canonical,
        discovered_query=query,
        company=company,
        title=title,
        posted_at=clean_text(result.get("publishedDate")),
        description=description,
        first_seen=now,
        last_seen=now,
    )
