# Auth Broker (Cloud Run)

Thin HTTP service between the Flutter client and Agent Runtime.

## Responsibilities

1. **Firebase JWT verification** — `patient_id` comes from the verified UID, never the request body.
2. **GCS signed upload URLs** — `POST /upload-url` returns a V4 signed PUT URL + `gs://` URI.
3. **Agent Runtime proxy** — `POST /prescription` calls the deployed reasoning engine (or local ADK Runner in dev).

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Health check |
| POST | `/upload-url` | Firebase JWT | Issue signed GCS PUT URL |
| POST | `/prescription` | Firebase JWT | Analyse image at `gcs_uri` |

## Local development

```bash
# From repo root — uses local ADK Runner (no Agent Runtime deploy needed)
export ENVIRONMENT=local
export DEV_PATIENT_ID=dev-patient-001
export USE_LOCAL_RUNNER=true
export GCS_BUCKET=medication-companion-uploads
export GOOGLE_CLOUD_PROJECT=medication-companion-dev

make auth-broker
```

> **Naming:** This is the **HTTP auth broker** (Firebase → GCS → Agent Runtime).
> A future **Pub/Sub** path for ambient agents is separate and will not reuse this
> Makefile target.

Flutter / script clients point `apiBaseUrl` at `http://localhost:8080`.

**Local dev note:** If your user ADC credentials cannot sign GCS URLs, use
`POST /upload-direct` (local-only) for server-side upload. The test script
auto-falls back; Flutter does the same when `ENVIRONMENT=local`.

## Production

Deploy to Cloud Run **with authentication required** (do not use `--allow-unauthenticated`).

Set env vars:

- `ENVIRONMENT=production`
- `GCS_BUCKET` — prescription upload bucket
- `AGENT_RUNTIME_RESOURCE` — full resource name from `deployment_metadata.json`
- `FIREBASE_PROJECT_ID` — for CORS allowlist

The broker service account needs:

- `roles/storage.objectCreator` on the upload bucket (signed URLs)
- `roles/aiplatform.user` (call Agent Runtime `streamQuery`)

## Client flow

```
Flutter → POST /upload-url (Bearer Firebase JWT)
       → PUT image to signed URL (no auth)
       → POST /prescription {gcs_uri, language} (Bearer Firebase JWT)
       ← PrescriptionResult JSON
```
