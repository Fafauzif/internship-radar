from __future__ import annotations

from datetime import date, datetime
import re
from zoneinfo import ZoneInfo
from typing import Any

from .models import AIExtraction, RawOpportunity


def _graduation_year(profile: dict[str, Any]) -> int:
    raw = profile["education"]["expected_graduation"]
    return int(str(raw)[:4])


def _is_indonesia(country: str, location: str) -> bool:
    country_n = str(country or "").strip().lower()
    if country_n in {"id", "idn", "indonesia"}:
        return True
    location_n = str(location or "").lower()
    return bool(re.search(r"\b(indonesia|jakarta|depok|bekasi|tangerang|bogor)\b", location_n))


def _deadline_passed(deadline: str, timezone_name: str = "Asia/Jakarta") -> bool:
    if not deadline:
        return False
    try:
        parsed = date.fromisoformat(deadline[:10])
        today = datetime.now(ZoneInfo(timezone_name)).date()
        return parsed < today
    except (ValueError, KeyError):
        return False


def evaluate_eligibility(opp: RawOpportunity, ai: AIExtraction, profile: dict[str, Any]) -> tuple[str, str, str]:
    """Return (eligibility_status, reason, timezone_compatibility)."""
    if _deadline_passed(ai.deadline or opp.deadline, str(profile.get("timezone", "Asia/Jakarta"))):
        return "NOT_RECOMMENDED", "Application deadline appears to have passed.", "UNKNOWN"

    grad_year = _graduation_year(profile)
    if ai.graduation_years and grad_year not in ai.graduation_years:
        return "NOT_RECOMMENDED", f"Listing targets graduation year(s) {ai.graduation_years}, not {grad_year}.", "UNKNOWN"

    if not ai.internship_like:
        return "NOT_RECOMMENDED", "Listing does not appear to be an internship/student placement.", "UNKNOWN"

    current = profile.get("current_availability", {})
    remote_part_time_only = bool(current.get("remote_part_time_only", True))

    work_mode = ai.work_mode if ai.work_mode != "UNKNOWN" else opp.remote_type
    schedule = ai.schedule_type

    timezone = "UNKNOWN"
    tz_text = ai.timezone_requirement.lower()
    if work_mode == "REMOTE":
        if not tz_text or "async" in tz_text:
            timezone = "GOOD"
        elif any(x in tz_text for x in ("asia", "apac", "indonesia", "gmt+7", "utc+7")):
            timezone = "GOOD"
        elif any(x in tz_text for x in ("us hours", "pacific time", "eastern time", "european hours", "cet")):
            timezone = "MODERATE"

    if remote_part_time_only:
        if work_mode == "REMOTE" and schedule in {"PART_TIME", "FLEXIBLE"}:
            if ai.local_work_authorization_required == "YES" and not _is_indonesia(opp.country, ai.location_requirement or opp.location):
                return "NEEDS_VERIFICATION", "Remote role may require local work authorization outside Indonesia.", timezone
            return "APPLY_NOW", "Remote and part-time/flexible requirements match current Semester 5 availability.", timezone
        if work_mode == "REMOTE" and schedule == "UNKNOWN":
            return "NEEDS_VERIFICATION", "Remote role found, but weekly schedule/hours are unclear.", timezone
        if schedule == "PART_TIME" and work_mode == "UNKNOWN":
            return "NEEDS_VERIFICATION", "Part-time schedule fits, but remote/on-site requirement is unclear.", timezone
        return "FUTURE_TARGET", "Current Semester 5 preference is remote part-time; this role is better suited from Semester 6 onward.", timezone

    return "APPLY_NOW", "No current availability conflict detected.", timezone
