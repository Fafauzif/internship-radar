from __future__ import annotations

import re
from datetime import date, datetime
from zoneinfo import ZoneInfo
from typing import Any

from .models import AIExtraction, RawOpportunity
from .text_utils import normalize_token


def _clamp(value: float) -> int:
    return max(0, min(100, round(value)))


def _profile_track(profile: dict[str, Any], category: str) -> dict[str, Any]:
    for track in profile.get("career_tracks", []):
        if track.get("name") == category:
            return track
    return {}


def _role_alignment(profile: dict[str, Any], category: str) -> int:
    track = _profile_track(profile, category)
    if not track:
        return 25
    priority = int(track.get("priority", 5))
    return {1: 100, 2: 92, 3: 84, 4: 78, 5: 72}.get(priority, 60)


def _experience_match(profile: dict[str, Any], category: str) -> int:
    track = _profile_track(profile, category)
    return _clamp(float(track.get("evidence_strength", 55)))


def _skill_match(profile: dict[str, Any], ai: AIExtraction) -> int:
    required = {normalize_token(x) for x in ai.required_skills if normalize_token(x)}
    preferred = {normalize_token(x) for x in ai.preferred_skills if normalize_token(x)}
    if not required and not preferred:
        return 60
    profile_skills = [normalize_token(x) for x in profile.get("skills", [])]

    def matched(skill: str) -> bool:
        tokens = set(skill.split())
        return any(skill == p or skill in p or p in skill or (tokens and tokens.issubset(set(p.split()))) for p in profile_skills)

    req_matches = sum(1 for x in required if matched(x))
    pref_matches = sum(1 for x in preferred if matched(x))
    req_score = req_matches / max(1, len(required))
    pref_score = pref_matches / max(1, len(preferred))
    return _clamp((req_score * 0.8 + pref_score * 0.2) * 100)


def _career_value(ai: AIExtraction) -> int:
    valuable = {
        "strategy", "analytics", "client_exposure", "ownership", "cross_functional",
        "brand", "growth", "partnerships", "regional_exposure", "mentorship", "research",
        "sustainability", "communications",
    }
    count = len(set(ai.career_value_signals) & valuable)
    return min(100, 45 + count * 9)


def _mission_alignment(profile: dict[str, Any], opp: RawOpportunity, ai: AIExtraction) -> int:
    interests = [normalize_token(x) for x in profile.get("interests", [])]
    text = normalize_token(" ".join([opp.title, opp.company, opp.description[:5000], " ".join(ai.responsibilities)]))
    hits = sum(1 for interest in interests if interest and interest in text)
    if ai.role_category == "Sustainability/Impact":
        hits += 2
    return min(100, 45 + hits * 12)


def career_fit_score(profile: dict[str, Any], opp: RawOpportunity, ai: AIExtraction) -> tuple[int, dict[str, int]]:
    parts = {
        "role_alignment": _role_alignment(profile, ai.role_category),
        "experience_evidence": _experience_match(profile, ai.role_category),
        "skills": _skill_match(profile, ai),
        "career_value": _career_value(ai),
        "industry_mission": _mission_alignment(profile, opp, ai),
    }
    total = (
        parts["role_alignment"] * 0.30
        + parts["experience_evidence"] * 0.25
        + parts["skills"] * 0.20
        + parts["career_value"] * 0.15
        + parts["industry_mission"] * 0.10
    )
    return _clamp(total), parts


def fit_band(score: int) -> str:
    if score >= 85:
        return "EXCELLENT"
    if score >= 72:
        return "STRONG"
    if score >= 58:
        return "POSSIBLE"
    return "WEAK"


def _days_until(deadline: str, timezone_name: str = "Asia/Jakarta") -> int | None:
    if not deadline:
        return None
    try:
        today = datetime.now(ZoneInfo(timezone_name)).date()
        return (date.fromisoformat(deadline[:10]) - today).days
    except (ValueError, KeyError):
        return None


def priority_bucket(eligibility: str, deadline: str, timezone_name: str = "Asia/Jakarta") -> str:
    if eligibility != "APPLY_NOW":
        return "P3"
    days = _days_until(deadline, timezone_name)
    if days is not None and days <= 3:
        return "P0"
    if days is not None and days <= 7:
        return "P1"
    if days is not None:
        return "P2"
    return "P2"


def action_priority(fit: int, eligibility: str, ai: AIExtraction) -> int:
    eligibility_conf = {"APPLY_NOW": 100, "NEEDS_VERIFICATION": 55, "FUTURE_TARGET": 35, "NOT_RECOMMENDED": 0}[eligibility]
    quality = _career_value(ai)
    compensation = {"PAID": 100, "UNKNOWN": 55, "UNPAID": 25}.get(ai.compensation_status, 55)
    # Application effort/expected value is neutral in MVP because the listing rarely provides enough information.
    effort_value = 60
    return _clamp(fit * 0.55 + eligibility_conf * 0.20 + quality * 0.10 + effort_value * 0.10 + compensation * 0.05)


def summary_reason(ai: AIExtraction, fit: int, parts: dict[str, int], eligibility: str) -> str:
    strongest = sorted(parts.items(), key=lambda x: x[1], reverse=True)[:2]
    labels = {
        "role_alignment": "role alignment",
        "experience_evidence": "existing experience",
        "skills": "skill overlap",
        "career_value": "career-learning value",
        "industry_mission": "industry/mission alignment",
    }
    strengths = ", ".join(labels[k] for k, _ in strongest)
    return f"{fit}/100 fit driven by {strengths}. Eligibility: {eligibility.replace('_', ' ').title()}."
