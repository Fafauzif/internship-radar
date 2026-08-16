from internship_radar.config import load_all


def test_project_configuration_is_valid():
    settings, profile, searches = load_all()
    assert settings["budgets"]["exa_monthly_budget_usd"] == 4.0
    assert profile["education"]["current_semester"] == 5
    assert len(searches["exa"]) >= 16
    assert len(searches["jsearch"]) >= 5
