from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class RawOpportunity:
    opportunity_id: str = ""
    dedupe_key: str = ""
    sources: list[str] = field(default_factory=list)
    source_job_ids: list[str] = field(default_factory=list)
    source_urls: list[str] = field(default_factory=list)
    application_url: str = ""
    canonical_url: str = ""
    discovered_query: str = ""
    company: str = ""
    title: str = ""
    location: str = ""
    city: str = ""
    country: str = ""
    remote_type: str = "UNKNOWN"
    employment_type: str = "UNKNOWN"
    posted_at: str = ""
    deadline: str = ""
    start_date: str = ""
    duration: str = ""
    compensation_status: str = "UNKNOWN"
    compensation_min: str = ""
    compensation_max: str = ""
    compensation_currency: str = ""
    compensation_period: str = ""
    description: str = ""
    first_seen: str = ""
    last_seen: str = ""
    status: str = "ACTIVE"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        for key in ("sources", "source_job_ids", "source_urls"):
            data[key] = " | ".join(dict.fromkeys(x for x in data[key] if x))
        return data


@dataclass
class AIExtraction:
    employer_name: str = ""
    normalized_title: str = ""
    role_category: str = "Other"
    internship_like: bool = False
    work_mode: str = "UNKNOWN"
    schedule_type: str = "UNKNOWN"
    working_hours: str = ""
    timezone_requirement: str = ""
    location_requirement: str = ""
    student_requirement: str = ""
    graduation_years: list[int] = field(default_factory=list)
    degree_requirements: list[str] = field(default_factory=list)
    required_skills: list[str] = field(default_factory=list)
    preferred_skills: list[str] = field(default_factory=list)
    responsibilities: list[str] = field(default_factory=list)
    career_value_signals: list[str] = field(default_factory=list)
    deadline: str = ""
    start_date: str = ""
    duration: str = ""
    compensation_status: str = "UNKNOWN"
    compensation_text: str = ""
    local_work_authorization_required: str = "UNKNOWN"
    visa_sponsorship: str = "UNKNOWN"
    evidence_quotes: list[str] = field(default_factory=list)
    missing_critical_fields: list[str] = field(default_factory=list)
    confidence: str = "MEDIUM"


@dataclass
class RadarRecord:
    opportunity_id: str
    company: str
    title: str
    category: str
    location: str
    work_mode: str
    schedule_type: str
    deadline: str
    start_date: str
    compensation: str
    eligibility: str
    eligibility_reason: str
    timezone_compatibility: str
    career_fit_score: int
    fit_band: str
    action_priority: int
    priority_bucket: str
    evaluation_confidence: str
    missing_critical_fields: str
    required_skills: str
    preferred_skills: str
    summary_reason: str
    application_url: str
    evaluated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RunStats:
    run_id: str
    mode: str
    started_at: str
    completed_at: str = ""
    status: str = "RUNNING"
    jsearch_requests: int = 0
    exa_requests: int = 0
    exa_cost_usd: float = 0.0
    gemini_calls: int = 0
    opportunities_discovered: int = 0
    opportunities_after_dedupe: int = 0
    opportunities_evaluated: int = 0
    raw_inserted: int = 0
    raw_updated: int = 0
    radar_inserted: int = 0
    radar_updated: int = 0
    error_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
