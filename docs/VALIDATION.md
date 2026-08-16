# Validation Record

This repository was checked before packaging on 16 August 2026.

## Automated checks completed

- Python source compilation: passed.
- Unit + mocked integration test suite: **18 passed**.
- Configuration validation: passed.
- Python package editable-install metadata: checked.
- Google Apps Script JavaScript syntax (`node --check`): passed.
- GitHub Actions YAML parsing: passed.
- Cross-language Python → JavaScript HMAC fixture: passed.
- Repository secret-pattern scan: no real API/private credentials found.
- ZIP extraction + repeat test run: performed after packaging.

## Regression cases covered

Tests include:

- JSearch/Exa normalization.
- canonical-URL duplicate merging.
- preservation of distinct recurring internships with different URLs.
- cheap role/internship filtering.
- Semester 5 eligibility behavior.
- graduation-year conflicts.
- Indonesia location detection without unsafe `ID` substring matching.
- deterministic score behavior.
- monthly query-plan limits.
- webhook HMAC signing.
- mocked end-to-end discovery → AI extraction → scoring → webhook sync.

## Important limitation

No live requests were made to JSearch, Exa, Gemini, or your Apps Script deployment because the repository intentionally contains no real credentials and your Apps Script web app does not exist until you deploy it. The first manual GitHub Actions run is therefore the final live integration test.

Run `python -m internship_radar.main --ping-webhook` after Apps Script deployment, then run the GitHub workflow manually once before relying on the daily schedule.
