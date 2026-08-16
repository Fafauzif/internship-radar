# Final MVP Architecture

## Goal

Build a personal opportunity intelligence system that reduces the number of listings the student must manually inspect without discarding the broader opportunity database.

## Components

```text
GitHub Actions (daily/manual)
        |
        v
Python orchestrator
   |            |
   v            v
 Exa          JSearch
   \            /
    v          v
Normalization + identity + dedupe
             |
             v
      Raw Opportunities
             |
             v
 deterministic prefilter
             |
             v
 Gemini factual extraction
             |
             v
 deterministic eligibility/scoring
             |
             v
   signed Apps Script webhook
       |                |
       v                v
 Google Sheets       MailApp digest
```

## Why Raw Opportunities exists

Raw Opportunities stores every **unique opportunity discovered by configured searches**, not just opportunities suitable for the current candidate. Personalized matching lives in Radar.

This gives the data model a useful separation:

```text
Opportunity facts != Candidate evaluation
```

A future profile (for example a friend's profile) can be evaluated against stored opportunities without changing the discovery layer.

## Why AI is not the scoring engine

Gemini is used for tasks that deterministic parsing performs poorly:

- distinguishing internship/student-program language;
- work mode and schedule interpretation;
- graduation requirements;
- degree restrictions;
- skills/responsibilities;
- work authorization language;
- deadline/start-date extraction;
- compensation text;
- controlled career-value signals.

It returns a strict schema.

Python then determines eligibility and numeric scoring. This makes repeated runs more stable, testable, and debuggable.

## Scoring

Career Fit:

```text
Role/function alignment       30%
Demonstrated evidence         25%
Skills                        20%
Career-learning value         15%
Industry/mission alignment    10%
```

Eligibility is not buried in that score. It is first classified as:

```text
APPLY_NOW
FUTURE_TARGET
NEEDS_VERIFICATION
NOT_RECOMMENDED
```

Action Priority is calculated separately. Deadline becomes a queue bucket (`P0`–`P3`) instead of artificially increasing the career quality of a weak job.

## Storage ownership

### Raw Opportunities
Machine-owned opportunity facts and source provenance.

### Radar
Machine evaluation + human interest/rejection feedback.

### Applications
Canonical human application workflow state.

This avoids maintaining application status in two places.

## Failure model

Each discovery source fails independently. Successful results from one source are still kept when the other source fails.

Run status:

```text
SUCCESS
PARTIAL_SUCCESS
FAILED
```

Run Log stores source usage and errors.

## Budget model

Apps Script Run Log is the persistent cross-run usage ledger because GitHub-hosted runners are ephemeral.

At run start:

```text
Python → signed usage_snapshot → Apps Script → Run Log totals
```

Python trims the query plan to remaining monthly allowance.

## Deliberately deferred

- ATS adapters
- embeddings/vector search
- preference-learning model
- resume tailoring
- cover letters
- automatic submission
- complex employer intelligence
