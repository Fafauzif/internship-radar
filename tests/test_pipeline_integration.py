from internship_radar.clients.exa import ExaSearchResult
from internship_radar.clients.webhook import UsageSnapshot
from internship_radar.models import AIExtraction
from internship_radar import pipeline


class FakeWebhook:
    last_payload = None

    def __init__(self, url, secret):
        pass

    def usage_snapshot(self):
        return UsageSnapshot()

    def post(self, payload, timeout=60):
        FakeWebhook.last_payload = payload
        return {
            "ok": True,
            "sync": {
                "raw_inserted": len(payload.get("raw_opportunities", [])),
                "raw_updated": 0,
                "radar_inserted": len(payload.get("radar", [])),
                "radar_updated": 0,
            },
        }


class FakeJSearch:
    def __init__(self, api_key):
        pass

    def search(self, query, country="id", date_posted="month"):
        return [{
            "job_id": "j1",
            "job_title": "Growth Marketing Intern",
            "employer_name": "Example Co",
            "job_location": "Jakarta, Indonesia",
            "job_country": "ID",
            "job_is_remote": True,
            "job_employment_type": "PART_TIME",
            "job_apply_link": "https://example.com/jobs/growth-intern",
            "job_description": "Remote part-time growth marketing internship with analytics and campaign work.",
        }]


class FakeExa:
    def __init__(self, api_key):
        pass

    def search(self, query, num_results=10, user_location="ID"):
        return ExaSearchResult(results=[{
            "id": "https://example.com/jobs/growth-intern",
            "url": "https://example.com/jobs/growth-intern",
            "title": "Growth Marketing Intern | Example Co",
            "highlights": ["Remote part-time marketing internship with analytics."],
        }], cost_usd=0.007)


class FakeGemini:
    def __init__(self, api_key, model):
        pass

    def extract(self, opportunity):
        return AIExtraction(
            employer_name="Example Co",
            normalized_title="Growth Marketing Intern",
            role_category="Marketing/Growth",
            internship_like=True,
            work_mode="REMOTE",
            schedule_type="PART_TIME",
            required_skills=["strategic marketing", "social media analytics"],
            career_value_signals=["growth", "analytics", "ownership"],
            compensation_status="UNKNOWN",
            confidence="HIGH",
        )


def test_end_to_end_pipeline_with_mocked_external_services(monkeypatch):
    monkeypatch.setattr(pipeline, "AppsScriptWebhookClient", FakeWebhook)
    monkeypatch.setattr(pipeline, "JSearchClient", FakeJSearch)
    monkeypatch.setattr(pipeline, "ExaClient", FakeExa)
    monkeypatch.setattr(pipeline, "GeminiClient", FakeGemini)
    for key in ["JSEARCH_API_KEY", "EXA_API_KEY", "GEMINI_API_KEY", "APPS_SCRIPT_WEBHOOK_URL", "WEBHOOK_SECRET"]:
        monkeypatch.setenv(key, "test-value")

    settings = {
        "gemini_model": "gemini-2.5-flash-lite",
        "budgets": {
            "jsearch_monthly_cap": 190,
            "exa_monthly_budget_usd": 4.0,
            "jsearch_max_per_run": 1,
            "exa_max_per_run": 1,
            "gemini_max_per_run": 5,
            "exa_estimated_search_cost_usd": 0.007,
        },
        "pipeline": {"exa_results_per_query": 10, "manual_budget_multiplier": 1.0},
        "notifications": {"enabled": True, "minimum_fit": 72},
    }
    profile = {
        "education": {"expected_graduation": "2028-08"},
        "current_availability": {"remote_part_time_only": True},
        "career_tracks": [{"name": "Marketing/Growth", "priority": 1, "evidence_strength": 95}],
        "skills": ["strategic marketing", "social media analytics"],
        "interests": [],
        "minimum_recommended_fit": 45,
    }
    searches = {
        "jsearch": [{"query": "growth intern Jakarta", "country": "id"}],
        "exa": [{"query": "growth marketing internship", "user_location": "ID"}],
    }

    run = pipeline.run_pipeline(settings, profile, searches)
    assert run.status == "SUCCESS"
    assert run.jsearch_requests == 1
    assert run.exa_requests == 1
    assert run.gemini_calls >= 1
    assert FakeWebhook.last_payload["action"] == "sync"
    assert len(FakeWebhook.last_payload["raw_opportunities"]) >= 1
    assert len(FakeWebhook.last_payload["radar"]) >= 1
