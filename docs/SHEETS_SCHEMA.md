# Google Sheets Schema

The canonical header definitions live in `apps-script/Code.gs`. `setupWorkbook()` creates/validates them.

## Raw Opportunities

Machine-owned database. Key: `opportunity_id`.

Important groups:

- Identity: `opportunity_id`, `dedupe_key`
- Provenance: `sources`, `source_job_ids`, `source_urls`, `discovered_query`
- Core facts: `company`, `title`, `location`, `country`, `remote_type`, `employment_type`
- Timing: `posted_at`, `deadline`, `start_date`, `duration`
- Compensation: status/min/max/currency/period
- Content: `description`
- Lifecycle: `first_seen`, `last_seen`, `status`

Repeated discoveries update the same row whenever identity/deduplication signals match.

## Radar

Personalized evaluation. Key: `opportunity_id`.

Machine-owned fields include:

- category
- work/schedule mode
- deadline/start date
- compensation
- eligibility + reason
- timezone compatibility
- career fit + fit band
- action priority + priority bucket
- evaluation confidence
- missing critical fields
- skills
- concise reasoning
- application URL

Human-owned fields preserved across machine sync:

```text
user_interest
rejection_reason
notes
```

## Applications

Canonical application-state table. Key: `opportunity_id`.

```text
opportunity_id
company
title
application_url
status
applied_date
interview_date
result
follow_up_date
notes
```

Use the Spreadsheet menu command **Add Selected Radar Row to Applications**. If already present, application-state fields are preserved.

## Profile

Readable summary only. The Python matching configuration is `config/profile.json`.

## Config

Readable operational summary only. The Python runtime configuration is `config/settings.json` and `config/searches.json`.

## Run Log

Persistent health + usage ledger:

- run ID/mode/timestamps/status
- JSearch request count
- Exa request count + reported cost
- Gemini call count
- discovered/deduped/evaluated counts
- inserted/updated counts
- error summary

The next GitHub Actions run reads current-month totals from this tab through the signed webhook before spending quota.
