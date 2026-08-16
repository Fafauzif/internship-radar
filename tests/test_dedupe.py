from internship_radar.dedupe import deduplicate
from internship_radar.models import RawOpportunity
from internship_radar.text_utils import build_opportunity_id


def make(source, url):
    oid, key = build_opportunity_id("Acme", "Marketing Intern", "Jakarta", url, source, source)
    return RawOpportunity(
        opportunity_id=oid,
        dedupe_key=key,
        sources=[source],
        source_job_ids=[source],
        source_urls=[url],
        canonical_url=url,
        application_url=url,
        company="Acme",
        title="Marketing Intern",
        location="Jakarta",
        description=f"description from {source}",
        first_seen="2026-08-15T00:00:00+00:00",
        last_seen="2026-08-16T00:00:00+00:00",
    )


def test_same_canonical_url_merges_cross_source():
    url = "https://careers.acme.example/jobs/marketing-intern"
    result = deduplicate([make("JSEARCH", url), make("EXA", url + "?utm_source=exa")])
    assert len(result) == 1
    assert set(result[0].sources) == {"JSEARCH", "EXA"}


def test_different_urls_are_not_destroyed_by_coarse_duplicate_key():
    # Could represent different seasonal intakes. Preserve both; dedupe_key can still group them.
    result = deduplicate([make("JSEARCH", "https://a.example/2026"), make("EXA", "https://b.example/2027")])
    assert len(result) == 2
    assert result[0].dedupe_key == result[1].dedupe_key
