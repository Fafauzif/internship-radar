from internship_radar.normalize import normalize_exa, normalize_jsearch


def test_jsearch_normalization_uses_apply_url_and_company():
    job = {
        "job_id": "abc123",
        "job_title": "Growth Marketing Intern",
        "employer_name": "Example Co",
        "job_location": "Jakarta, Indonesia",
        "job_country": "ID",
        "job_is_remote": True,
        "job_apply_link": "https://example.com/job?utm_source=foo",
        "job_description": "Part-time growth marketing internship.",
    }
    opp = normalize_jsearch(job, "growth internship Jakarta")
    assert opp.company == "Example Co"
    assert opp.application_url.startswith("https://example.com/job")
    assert "utm_source" not in opp.canonical_url
    assert opp.remote_type == "REMOTE"
    assert opp.opportunity_id.startswith("opp_")


def test_exa_company_guess_from_title():
    result = {
        "id": "https://careers.example.com/123",
        "url": "https://careers.example.com/123",
        "title": "Marketing Intern | Acme",
        "highlights": ["Join our marketing internship program."],
    }
    opp = normalize_exa(result, "marketing internships")
    assert opp.company == "Acme"
    assert "internship" in opp.description.lower()
