# Security Notes

## Secrets

Never commit real credentials. The repository expects secrets only through environment variables / GitHub Actions secrets:

```text
JSEARCH_API_KEY
EXA_API_KEY
GEMINI_API_KEY
APPS_SCRIPT_WEBHOOK_URL
WEBHOOK_SECRET
```

The webhook URL is treated as sensitive operational configuration even though authentication does not rely on URL secrecy.

## Apps Script authentication

Apps Script web apps do not expose a convenient arbitrary-header authentication surface to `doPost(e)`, so the system signs the request body.

Python sends:

```text
timestamp
nonce
payload_b64
signature
```

The signature is:

```text
HMAC-SHA256(WEBHOOK_SECRET, timestamp + "." + nonce + "." + payload_b64)
```

Apps Script rejects:

- missing/malformed fields;
- signatures that do not match;
- timestamps older/newer than five minutes;
- recently reused nonces.

The URL alone is therefore insufficient to write to the spreadsheet.

## Formula injection protection

Job titles/descriptions are untrusted third-party text. Apps Script prefixes dangerous leading formula characters before writing strings that could otherwise execute as Google Sheets formulas.

## Spreadsheet permissions

No Google Cloud service account is used. The bound Apps Script runs as the spreadsheet owner and writes only through `SpreadsheetApp` after signature verification.

## Gemini privacy

The configured matching profile excludes:

- personal email;
- phone number;
- exact address;
- GPA;
- unrelated personal records.

Gemini receives the job listing for factual extraction. The deterministic scoring layer uses the local redacted profile; the full master personal file is not sent to Gemini.

## Human-owned fields

Machine sync preserves these Radar fields:

```text
user_interest
rejection_reason
notes
```

Application pipeline fields live canonically in the Applications tab and are also preserved when a Radar row is added again.

## Budget safety

The pipeline asks Apps Script for current-month usage **before** calling discovery APIs. If that state read fails, the pipeline fails closed rather than spending API quota without knowing remaining budget.

JSearch and Exa discovery requests are not automatically retried inside the API client, so hidden retries cannot silently multiply a per-run request budget.
