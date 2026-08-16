from __future__ import annotations

import json
import os
import time
from typing import Any

from ..http_utils import APIError, request_json
from ..models import AIExtraction, RawOpportunity


ROLE_CATEGORIES = [
    "Marketing/Growth",
    "Consulting/Strategy",
    "Business Development",
    "Communication/PR",
    "Sustainability/Impact",
    "Other",
]


def _string_array() -> dict[str, Any]:
    return {"type": "ARRAY", "items": {"type": "STRING"}}


RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "employer_name": {"type": "STRING"},
        "normalized_title": {"type": "STRING"},
        "role_category": {"type": "STRING", "enum": ROLE_CATEGORIES},
        "internship_like": {"type": "BOOLEAN"},
        "work_mode": {"type": "STRING", "enum": ["REMOTE", "HYBRID", "ONSITE", "UNKNOWN"]},
        "schedule_type": {"type": "STRING", "enum": ["PART_TIME", "FULL_TIME", "FLEXIBLE", "UNKNOWN"]},
        "working_hours": {"type": "STRING"},
        "timezone_requirement": {"type": "STRING"},
        "location_requirement": {"type": "STRING"},
        "student_requirement": {"type": "STRING"},
        "graduation_years": {"type": "ARRAY", "items": {"type": "INTEGER"}},
        "degree_requirements": _string_array(),
        "required_skills": _string_array(),
        "preferred_skills": _string_array(),
        "responsibilities": _string_array(),
        "career_value_signals": {
            "type": "ARRAY",
            "items": {
                "type": "STRING",
                "enum": [
                    "strategy", "analytics", "client_exposure", "ownership", "cross_functional",
                    "brand", "growth", "partnerships", "regional_exposure", "mentorship",
                    "research", "sustainability", "communications",
                ],
            },
        },
        "deadline": {"type": "STRING"},
        "start_date": {"type": "STRING"},
        "duration": {"type": "STRING"},
        "compensation_status": {"type": "STRING", "enum": ["PAID", "UNPAID", "UNKNOWN"]},
        "compensation_text": {"type": "STRING"},
        "local_work_authorization_required": {"type": "STRING", "enum": ["YES", "NO", "UNKNOWN"]},
        "visa_sponsorship": {"type": "STRING", "enum": ["YES", "NO", "UNKNOWN"]},
        "evidence_quotes": _string_array(),
        "missing_critical_fields": _string_array(),
        "confidence": {"type": "STRING", "enum": ["HIGH", "MEDIUM", "LOW"]},
    },
    "required": [
        "employer_name", "normalized_title", "role_category", "internship_like", "work_mode",
        "schedule_type", "working_hours", "timezone_requirement", "location_requirement",
        "student_requirement", "graduation_years", "degree_requirements", "required_skills",
        "preferred_skills", "responsibilities", "career_value_signals", "deadline", "start_date",
        "duration", "compensation_status", "compensation_text", "local_work_authorization_required",
        "visa_sponsorship", "evidence_quotes", "missing_critical_fields", "confidence",
    ],
}


class GeminiClient:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash-lite") -> None:
        self.api_key = api_key
        self.model = model
        # Free-tier limits can vary by project. A conservative default prevents bursty
        # sequential extraction from immediately tripping RPM limits; override with
        # GEMINI_MIN_INTERVAL_SECONDS=0 if your project has a higher verified limit.
        self.min_interval_seconds = max(0.0, float(os.getenv("GEMINI_MIN_INTERVAL_SECONDS", "4.2")))
        self._last_request_at = 0.0

    def _throttle(self) -> None:
        if self.min_interval_seconds <= 0 or self._last_request_at <= 0:
            return
        remaining = self.min_interval_seconds - (time.monotonic() - self._last_request_at)
        if remaining > 0:
            time.sleep(remaining)

    def extract(self, opportunity: RawOpportunity) -> AIExtraction:
        description = (opportunity.description or "")[:24000]
        prompt = f"""You are extracting factual internship information for a personal career dashboard.
Do NOT score the candidate. Do NOT guess missing facts. Use UNKNOWN/empty values when absent.
An internship-like role includes internships, traineeships, student programs, summer analyst programs,
and other temporary student work placements. Keep evidence_quotes short and verbatim from the supplied listing.
Dates should use YYYY-MM-DD when explicitly derivable; otherwise preserve a concise original expression or leave blank.

LISTING
Title: {opportunity.title}
Company: {opportunity.company}
Location: {opportunity.location}
Known remote flag: {opportunity.remote_type}
Known employment type: {opportunity.employment_type}
Posted: {opportunity.posted_at}
URL: {opportunity.canonical_url or opportunity.application_url}
Description/excerpts:
{description}
"""
        self._throttle()
        self._last_request_at = time.monotonic()
        data = request_json(
            "POST",
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
            json_body={
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "responseSchema": RESPONSE_SCHEMA,
                },
            },
            timeout=60,
            attempts=2,
        )
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(text)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise APIError(f"Gemini returned an unexpected structured response: {data}") from exc
        return AIExtraction(**{k: parsed.get(k, getattr(AIExtraction(), k)) for k in AIExtraction.__dataclass_fields__})
