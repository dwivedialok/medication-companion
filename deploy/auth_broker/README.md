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

make local-auth-broker
```

> **Naming:** This is the **HTTP auth broker** (Firebase → GCS → Agent Runtime).
> A future **Pub/Sub** path for ambient agents is separate and will not reuse this
> Makefile target. Architecture: Pub/Sub push → prescription worker → private
> Agent Runtime `streamQuery` (not ADK `/trigger/pubsub`); clients poll
> `GET /jobs/{job_id}`. See [`docs/BACKLOG.md`](../../docs/BACKLOG.md) →
> "Why worker + streamQuery, not ADK `/trigger/pubsub`".

Flutter / script clients point `apiBaseUrl` at `http://localhost:8080`.

**Local dev note:** If your user ADC credentials cannot sign GCS URLs, use
`POST /upload-direct` (local-only) for server-side upload. The test script
auto-falls back; Flutter does the same when `ENVIRONMENT=local`.

## Production

The auth broker runs on Cloud Run with **`--allow-unauthenticated`** at the IAM
layer because [Firebase Hosting rewrites](https://firebase.google.com/docs/hosting/cloud-run)
proxy browser traffic without Google IAM identity tokens. Sensitive routes still
verify **Firebase JWT** in `auth_broker/auth.py`; `/health` is intentionally public.

```
Browser ──HTTPS──▶ https://<project>.web.app
                        │
                        │  (Firebase Hosting rewrite, no IAM token)
                        ▼
                  medication-companion-broker (Cloud Run, public invoke)
                        │
                        │  (Vertex AI client, app_sa creds)
                        ▼
                  Agent Runtime (Reasoning Engine, private)
```

### Infrastructure (Terraform)

`deployment/terraform/{single-project,cicd}/auth_broker.tf` owns:

- Artifact Registry Docker repo (`<project>-broker`)
- `google_cloud_run_v2_service.auth_broker` (skeleton — image and dynamic env
  ignored via `lifecycle.ignore_changes`)
- `roles/iam.serviceAccountTokenCreator` self-binding on `app_sa` (V4 signed
  PUT URLs)

Run `make infra-apply` (single-project) or `terraform apply` in the cicd
module to provision these.

### Revisions (deploy script)

`deploy/auth_broker/deploy.sh` (or `make deploy-auth-broker`) builds the
Docker image, pushes to Artifact Registry, and runs `gcloud run deploy`
against the Terraform-managed service to update only:

- `--image` (the new container tag)
- `--allow-unauthenticated` (required for Hosting rewrites)
- `--update-env-vars=AGENT_RUNTIME_RESOURCE=…` (read from
  `deployment_metadata.json` produced by `make deploy`)

Static env vars (`ENVIRONMENT`, `GCS_BUCKET`, `FIREBASE_PROJECT_ID`) come from
Terraform.

### Required IAM

- `roles/storage.admin` on the broker SA (signed URL bucket access)
- `roles/aiplatform.user` (call Agent Runtime `streamQuery`)
- `roles/iam.serviceAccountTokenCreator` self-binding (sign blobs for V4 URLs) — Terraform
- `roles/run.invoker` for `allUsers` on the broker service — set by `make deploy-auth-broker`

## Client flow

```
Flutter → POST /upload-url      (Firebase JWT, via Hosting rewrite)
       → PUT image to GCS       (signed URL, no auth)
       → POST /prescription     (Firebase JWT, via Hosting rewrite)
       ← PrescriptionResult JSON
```
