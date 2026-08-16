from internship_radar.eligibility import evaluate_eligibility
from internship_radar.models import AIExtraction, RawOpportunity

PROFILE = {
    "education": {"expected_graduation": "2028-08"},
    "current_availability": {"remote_part_time_only": True},
}


def test_remote_part_time_is_apply_now():
    opp = RawOpportunity(country="ID", location="Jakarta")
    ai = AIExtraction(internship_like=True, work_mode="REMOTE", schedule_type="PART_TIME", confidence="HIGH")
    status, _, tz = evaluate_eligibility(opp, ai, PROFILE)
    assert status == "APPLY_NOW"
    assert tz == "GOOD"


def test_full_time_onsite_is_future_target():
    opp = RawOpportunity(country="ID", location="Jakarta")
    ai = AIExtraction(internship_like=True, work_mode="ONSITE", schedule_type="FULL_TIME")
    status, _, _ = evaluate_eligibility(opp, ai, PROFILE)
    assert status == "FUTURE_TARGET"


def test_wrong_graduation_year_rejected():
    opp = RawOpportunity(country="SG", location="Singapore")
    ai = AIExtraction(internship_like=True, work_mode="REMOTE", schedule_type="PART_TIME", graduation_years=[2027])
    status, reason, _ = evaluate_eligibility(opp, ai, PROFILE)
    assert status == "NOT_RECOMMENDED"
    assert "2028" in reason


def test_indonesia_detection_does_not_match_id_substring_in_foreign_location():
    from internship_radar.eligibility import _is_indonesia
    assert _is_indonesia("US", "Midtown, New York") is False
    assert _is_indonesia("ID", "") is True
    assert _is_indonesia("", "Jakarta, Indonesia") is True
