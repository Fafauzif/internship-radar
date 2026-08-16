# Setup Guide

## 1. Get the three API keys

### JSearch

If using RapidAPI JSearch:

1. Subscribe to the JSearch free/basic plan.
2. Copy your RapidAPI key.
3. GitHub secret name: `JSEARCH_API_KEY`.
4. Optional GitHub repository variable: `JSEARCH_BACKEND=rapidapi` (this is the default).

The project also supports a direct OpenWeb Ninja JSearch key. For that path set `JSEARCH_BACKEND=openwebninja`.

### Exa

1. Create an Exa account.
2. Create/copy an API key from the Exa dashboard.
3. GitHub secret name: `EXA_API_KEY`.

### Gemini

1. Create a Gemini API key in Google AI Studio.
2. GitHub secret name: `GEMINI_API_KEY`.

The default model is `gemini-2.5-flash-lite`. Change `config/settings.json` later if desired.

---

## 2. Create the Google Sheet

Create one blank Google Spreadsheet, for example:

```text
AI Internship Radar
```

You do **not** need to create tabs manually.

Open:

```text
Extensions → Apps Script
```

Replace the default script with the contents of:

```text
apps-script/Code.gs
```

Optional: if you want the supplied manifest, enable **Show "appsscript.json" manifest file in editor** in Apps Script Project Settings and copy `apps-script/appsscript.json`.

Save the Apps Script project.

---

## 3. Bootstrap the workbook

In Apps Script, run:

```javascript
setupWorkbook()
```

The first run will ask you to authorize Spreadsheet/Mail permissions.

It safely creates or validates these tabs:

```text
Raw Opportunities
Radar
Applications
Profile
Config
Run Log
```

It will refuse to silently overwrite a pre-existing tab whose header schema does not match.

Reload the spreadsheet. You should now see an **Internship Radar** menu.

---

## 4. Generate the webhook secret

Generate one strong random secret locally. Example:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copy the output.

In the spreadsheet:

```text
Internship Radar → Set Webhook Secret
```

Paste the generated secret.

You will later store the **exact same value** in GitHub as:

```text
WEBHOOK_SECRET
```

Do not commit this value to the repository.

---

## 5. Set your notification email

In the spreadsheet:

```text
Internship Radar → Set Notification Email
```

Enter the email address where you want the digest delivered.

Then choose:

```text
Internship Radar → Send Test Email
```

Email is sent through Apps Script `MailApp`; GitHub never gets your Gmail password and the script does not need inbox-reading access.

---

## 6. Deploy the Apps Script webhook

In Apps Script:

```text
Deploy → New deployment → Web app
```

Recommended settings:

```text
Execute as: Me
Who has access: Anyone
```

The endpoint must be reachable by GitHub Actions, so GitHub cannot be required to perform an interactive Google sign-in.

Copy the production URL ending in:

```text
/exec
```

This becomes the GitHub secret:

```text
APPS_SCRIPT_WEBHOOK_URL
```

Although the web-app URL is externally reachable, write requests require a valid timestamped HMAC-SHA256 signature and nonce. A caller with only the URL cannot create a valid sync request.

If you later change `Code.gs`, update the Web App deployment to a new version.

---

## 7. Create the GitHub repository

Upload the repository contents.

Go to:

```text
Repository → Settings → Secrets and variables → Actions
```

### Secrets

Add:

```text
JSEARCH_API_KEY
EXA_API_KEY
GEMINI_API_KEY
APPS_SCRIPT_WEBHOOK_URL
WEBHOOK_SECRET
```

### Variable (optional)

Under **Variables**, add:

```text
JSEARCH_BACKEND = rapidapi
```

If you omit it, RapidAPI is the default.

---

## 8. First run

Go to:

```text
Actions → Internship Radar → Run workflow
```

Choose `manual`.

The job will:

1. install Python dependencies;
2. validate JSON configuration;
3. run the test suite;
4. query Apps Script for current monthly usage;
5. run JSearch + Exa within remaining caps;
6. store every unique discovered opportunity in Raw Opportunities;
7. evaluate plausible target internships;
8. upsert Radar;
9. log the run;
10. email you only if new strong `APPLY_NOW` matches were inserted.

---

## 9. Daily schedule

The supplied workflow runs at:

```text
08:17 Asia/Jakarta
```

It deliberately avoids the top of the hour, when scheduled GitHub Actions are more likely to be delayed under load.

Change `.github/workflows/radar.yml` if you want another time.

---

## 10. What to edit first

### Search coverage

Edit:

```text
config/searches.json
```

The scheduler rotates through the query pool instead of burning every query every day.

### Budget

Edit:

```text
config/settings.json
```

Defaults:

```json
{
  "jsearch_monthly_cap": 190,
  "exa_monthly_budget_usd": 4.0,
  "jsearch_max_per_run": 5,
  "exa_max_per_run": 16,
  "gemini_max_per_run": 40
}
```

### Candidate profile

Edit:

```text
config/profile.json
```

The supplied profile deliberately excludes email, phone, GPA, and other unnecessary personal data.

When Semester 6 begins, change the availability rules in this file rather than rewriting the pipeline.

---

## Troubleshooting

### `Could not read monthly usage ... refusing to spend API budget`

This is intentional fail-closed behavior. Check:

- Apps Script deployment URL is the production `/exec` URL;
- `WEBHOOK_SECRET` matches exactly on both sides;
- `setupWorkbook()` was run;
- Apps Script deployment is still active.

### Apps Script returns `Invalid signature`

The two `WEBHOOK_SECRET` values do not match, or a proxy/tool altered the signed payload.

### Apps Script returns `Expired request timestamp`

The machine clock is badly incorrect. GitHub-hosted runners should not normally hit this.

### No email received

Email is intentionally suppressed unless the run inserts at least one new `APPLY_NOW` opportunity meeting `notifications.minimum_fit` (default 72). Use **Send Test Email** to test mail separately.

### An opportunity is in Raw but not Radar

Expected. Raw is broad discovery. Radar only evaluates listings that pass the inexpensive internship + target-role prefilter and the configured Gemini per-run cap.

### A source is failing

The other source still runs. Check `Run Log → error_summary`. A partial source failure is recorded as `PARTIAL_SUCCESS`.
