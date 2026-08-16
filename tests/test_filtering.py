from internship_radar.filtering import is_candidate_for_ai
from internship_radar.models import RawOpportunity


def test_candidate_filter_keeps_target_internship():
    opp = RawOpportunity(title="Growth Marketing Intern", description="Help with campaign analytics")
    assert is_candidate_for_ai(opp)


def test_candidate_filter_rejects_senior_non_internship():
    opp = RawOpportunity(title="Senior Marketing Manager", description="Lead growth strategy")
    assert not is_candidate_for_ai(opp)


def test_query_text_alone_does_not_force_ai_evaluation():
    opp = RawOpportunity(title="Company homepage", description="Welcome to our company", discovered_query="marketing internship")
    assert not is_candidate_for_ai(opp)
