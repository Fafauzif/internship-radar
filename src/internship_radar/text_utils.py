from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "gclid", "fbclid", "ref", "referrer", "source", "trk", "trackingid",
}


def clean_text(value: object, max_len: int | None = None) -> str:
    if value is None:
        return ""
    text = re.sub(r"\s+", " ", str(value)).strip()
    if max_len is not None:
        return text[:max_len]
    return text


def normalize_token(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def normalize_url(url: str) -> str:
    if not url:
        return ""
    try:
        parts = urlsplit(url.strip())
        query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k.lower() not in TRACKING_PARAMS]
        path = re.sub(r"/+", "/", parts.path).rstrip("/") or "/"
        return urlunsplit((parts.scheme.lower() or "https", parts.netloc.lower(), path, urlencode(query), ""))
    except Exception:
        return url.strip()


def stable_hash(value: str, prefix: str = "opp") -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]
    return f"{prefix}_{digest}"


def make_dedupe_key(company: str, title: str, location: str) -> str:
    company_n = normalize_token(company)
    title_n = normalize_title(title)
    location_n = normalize_token(location)
    if company_n and title_n:
        return f"{company_n}|{title_n}|{location_n}"
    return ""


def normalize_title(title: str) -> str:
    title = normalize_token(title)
    removable = {
        "internship", "intern", "trainee", "part time", "full time",
        "remote", "hybrid", "onsite", "on site", "summer", "winter",
    }
    for phrase in sorted(removable, key=len, reverse=True):
        title = re.sub(rf"\b{re.escape(phrase)}\b", " ", title)
    return re.sub(r"\s+", " ", title).strip()


def build_opportunity_id(company: str, title: str, location: str, canonical_url: str, source: str, source_job_id: str) -> tuple[str, str]:
    """Build a loss-averse identity plus a softer duplicate-group hint.

    Canonical URL is preferred so recurring internships with the same title/company/location
    in different seasons do not overwrite one another. `dedupe_key` remains available for
    grouping/suspicion, but is only used as the identity fallback when no URL/source ID exists.
    """
    dedupe_key = make_dedupe_key(company, title, location)
    normalized_url = normalize_url(canonical_url)
    if normalized_url:
        return stable_hash(normalized_url), dedupe_key
    if source_job_id:
        return stable_hash(f"{source}|{source_job_id}"), dedupe_key
    if dedupe_key:
        return stable_hash(dedupe_key), dedupe_key
    fallback = f"{source}|{title}|{location}"
    return stable_hash(fallback), dedupe_key
