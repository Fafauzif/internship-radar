from internship_radar.models import AIExtraction, RawOpportunity
from internship_radar.scoring import career_fit_score, fit_band, priority_bucket

PROFILE = {
    "career_tracks": [
        {"name": "Marketing/Growth", "priority": 1, "evidence_strength": 95},
        {"name": "Consulting/Strategy", "priority": 2, "evidence_strength": 90},
    ],
    "skills": ["strategic marketing", "social media analytics", "copywriting", "partnership development"],
    "interests": ["sustainability", "climate"],
}


def test_strong_marketing_role_scores_well():
    opp = RawOpportunity(title="Growth Marketing Intern", description="Growth analytics and campaign strategy")
    ai = AIExtraction(
        internship_like=True,
        role_category="Marketing/Growth",
        required_skills=["strategic marketing", "social media analytics"],
        career_value_signals=["growth", "analytics", "ownership", "cross_functional"],
    )
    score, _ = career_fit_score(PROFILE, opp, ai)
    assert score >= 80
    assert fit_band(score) in {"STRONG", "EXCELLENT"}


def test_deadline_is_priority_bucket_not_fit_component():
    assert priority_bucket("APPLY_NOW", "") == "P2"
    assert priority_bucket("FUTURE_TARGET", "2026-08-17") == "P3"
