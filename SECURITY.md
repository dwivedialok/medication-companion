# Security Policy

Medication Companion is an **educational prototype**, not a clinically validated
medical device. This policy covers **software and infrastructure security** for
the repository and deployed demo environment.

## Supported versions

| Version / branch | Supported |
|------------------|-----------|
| `main` (latest)  | Yes       |
| Other branches   | Best effort only |

The public demo at `https://medication-companion-dev.web.app` tracks `main`.
There is no separate long-term support release cadence.

## Reporting a vulnerability

**Please do not open public GitHub issues for security vulnerabilities.**

Report privately using one of:

1. **Preferred:** [GitHub Security Advisories](https://github.com/3amwave/medication-companion/security/advisories/new) — *Report a vulnerability* on the repository.
2. **Alternative:** Contact [@3amwave](https://github.com/3amwave) via GitHub with subject `Security: medication-companion`.

Include:

- Description of the issue and potential impact
- Steps to reproduce (URLs, request/response samples, screenshots)
- Affected component (auth broker, worker, Flutter app, Firebase rules, etc.)
- Your suggested severity (if known)

We will acknowledge receipt within **7 days** and aim to provide a fix or mitigation
plan within **30 days** for confirmed issues on `main`. Timelines are best-effort for
this capstone project.

## Scope

**In scope**

- Authentication or authorization bypass (Firebase JWT, `patient_id` binding)
- Cross-tenant access to another patient's jobs, prescriptions, or memory
- Unauthenticated access to private Cloud Run services (Agent Runtime, worker)
- GCS signed-URL issues (upload/read URL scoped to wrong patient or excessive TTL)
- Injection or policy bypass in patient-facing agent output
- Secrets or credentials committed to the repository

**Out of scope**

- Missing clinical features (dose advice, refill reminders, EMR integration)
- Incorrect drug interaction data in the curated SQLite matrix (report as a data bug via a normal issue, not security)
- Social engineering, physical access, or third-party service outages (Google Cloud, Firebase, Kaggle)
- Denial-of-service against the public demo without a demonstrated exploit path

## Security architecture (summary)

- **Auth broker** is the only client-facing HTTP API; Firebase JWT is verified on every protected route; `patient_id` is derived from the verified UID, never from the request body.
- **Agent Runtime** and the **prescription worker** are private; invoked with service-account credentials only.
- **Prescription images** are stored in GCS under `prescriptions/{patient_id}/`; Memory Bank stores resolved generic names only — not images or clinical notes.
- **Firestore** holds async job metadata and results; list/read endpoints filter by authenticated `patient_id`.

See [`docs/architecture.md`](docs/architecture.md#security-model) and
[`AGENTS.md`](AGENTS.md) for hard rules enforced in code review.

## Safe disclosure

We appreciate responsible disclosure. With your permission, we will credit reporters
in the advisory or release notes. Please allow reasonable time to patch before public
disclosure.

## Medical disclaimer

Security reports about **medical accuracy** (wrong interaction severity, missed
drug match) are important product feedback but are not treated as CVE-class
vulnerabilities unless they stem from an auth, tenancy, or data-leak flaw. Use a
normal GitHub issue for clinical-data quality.
