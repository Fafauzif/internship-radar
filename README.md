# AI Internship Radar

Personal internship discovery + career intelligence automation for one university student.

The system intentionally optimizes for **usefulness, low cost, reliability, and low maintenance** rather than maximum technical complexity.

## What it does

Daily pipeline:

```text
GitHub Actions
    ↓
Python
    ↓
Exa + JSearch
    ↓
Normalize + deduplicate
    ↓
Raw Opportunities (every unique opportunity discovered by configured searches)
    ↓
Cheap deterministic internship/role filter
    ↓
Gemini structured fact extraction
    ↓
Python eligibility + deterministic scoring
    ↓
Radar
    ↓
Apps Script → Google Sheets + useful-only email digest
```

The raw database is intentionally broader than the personalized Radar. That means the stored opportunities can later be re-evaluated for a different profile without changing the discovery architecture.

## MVP scope

Included:

- JSearch discovery
- Exa discovery (primary exploration source)
- Stable normalization and deduplication
- Raw Opportunities database in Google Sheets
- Gemini structured extraction (not free-form AI scoring)
- Semester/availability/graduation eligibility logic
- Deterministic career-fit scoring
- `APPLY_NOW`, `FUTURE_TARGET`, `NEEDS_VERIFICATION`, `NOT_RECOMMENDED`
- User interest feedback in Radar
- Separate Applications tracker as the canonical application-state table
- Daily email only when genuinely useful new `APPLY_NOW` matches appear
- Monthly API budget guards backed by Apps Script Run Log
- Signed Apps Script webhook (HMAC + timestamp + replay protection)
- Daily + manual GitHub Actions runs
- Unit/integration tests

Not included:

- ATS-specific integrations
- vector database / embeddings
- multi-agent architecture
- PostgreSQL / backend database
- automatic applications
- resume/cover-letter generation
- company-prestige scraping

## Google Sheets tabs

`setupWorkbook()` creates:

1. **Raw Opportunities** — machine-owned unique opportunity database.
2. **Radar** — personalized evaluation + human `YES / MAYBE / NO` feedback.
3. **Applications** — canonical manual application pipeline.
4. **Profile** — readable profile summary.
5. **Config** — readable runtime/budget summary.
6. **Run Log** — health, request usage, cost estimates, errors.

From the **Radar** tab, select a row and use **Internship Radar → Add Selected Radar Row to Applications**. Existing application fields are preserved on repeated adds.

## Required secrets

GitHub Actions needs exactly five secrets:

```text
JSEARCH_API_KEY
EXA_API_KEY
GEMINI_API_KEY
APPS_SCRIPT_WEBHOOK_URL
WEBHOOK_SECRET
```

Optional repository variable:

```text
JSEARCH_BACKEND=rapidapi
```

Use `openwebninja` instead if your JSearch key came directly from OpenWeb Ninja.

There is **no Google Cloud service account**, Google Sheets API key, Gmail password, or OAuth refresh token.

## Default budget policy

Configured in `config/settings.json`:

```text
JSearch monthly safety cap: 190 requests
JSearch scheduled max/run: 5 requests
Exa monthly usage budget: $4.00
Exa scheduled max/run: 16 searches
Gemini max/run: 40 evaluated opportunities
Gemini default pacing: one request every 4.2s (overrideable)
```

At one scheduled run/day, 16 Exa searches/day is at most 496 searches in a 31-day month. At the configured $0.007 standard-search estimate that is about $3.47 of Exa usage. Actual Exa response cost is logged and used by the next run's budget guard.

The budget guard **fails closed**: if Python cannot read the monthly usage snapshot from Apps Script, it refuses to call the paid/quota-limited discovery APIs.

## Why Gemini 2.5 Flash-Lite by default?

`gemini-2.5-flash-lite` remains configurable in `config/settings.json` and was selected because its standard Gemini Developer API tier is currently documented with free input/output usage. The system only asks Gemini to extract structured facts; Python owns eligibility and scoring.

## Quick start

See **[SETUP.md](SETUP.md)**. The short version:

1. Get JSearch, Exa, and Gemini keys.
2. Create one blank Google Sheet.
3. Paste `apps-script/Code.gs` into the bound Apps Script project.
4. Run `setupWorkbook()`.
5. Set notification email + webhook secret from the new Spreadsheet menu.
6. Deploy Apps Script as a Web App and copy the `/exec` URL.
7. Put the five secrets in GitHub Actions.
8. Run the workflow manually once.

## Local validation

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest -q
PYTHONPATH=src python -m internship_radar.main --validate-only
```

After configuring the Apps Script URL and webhook secret locally:

```bash
PYTHONPATH=src python -m internship_radar.main --ping-webhook
```

## Design principles

- **Raw data and personalized intelligence are separate.**
- **AI extracts; deterministic code decides.**
- **Eligibility is a state/gate, not merely 20% of a score.**
- **Deadline changes urgency, not career quality.**
- **Human-edited spreadsheet fields are never blindly overwritten.**
- **A source failure produces partial success rather than destroying results from other sources.**
- **Do not spend API budget if state/usage cannot be verified.**

## Documentation

- [Setup](SETUP.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Sheet schema](docs/SHEETS_SCHEMA.md)
- [Security](SECURITY.md)
