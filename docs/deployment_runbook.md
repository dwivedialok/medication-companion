# Deployment runbook

Operational cheat sheet for Medication Companion. One command per scenario —
no narrative. For architecture, see [AGENTS.md](../AGENTS.md) and
[deploy/auth_broker/README.md](../deploy/auth_broker/README.md).

**Manual smoke tests (A1→C ladder):** [smoke_test_cheatsheet.md](smoke_test_cheatsheet.md)

The deploy stack is split across four tools:

| Layer | Tool | Source of truth |
|-------|------|-----------------|
| IAM, buckets, Cloud Run skeleton, Artifact Registry, GitHub WIF | Terraform | [`deployment/terraform/`](../deployment/terraform/) |
| Agent Runtime (ADK pipeline) | `agents-cli deploy` | `deployment_metadata.json` |
| Auth broker image + revision | `make deploy-auth-broker` (shell + gcloud) | `deploy/auth_broker/deploy.sh` |
| Prescription worker (Pub/Sub push) | `make deploy-prescription-worker` | `deploy/workers/deploy.sh` |
| Flutter PWA | `firebase deploy --only hosting` | `firebase.json` |

## §0 Prerequisites

```bash
# One-time, on your laptop
gcloud auth login
gcloud auth application-default login
uv sync
npm install -g firebase-tools
# Flutter SDK + Firebase CLI must be on PATH

# Per-shell exports (replace with the target env)
export GCP_PROJECT=medication-companion-dev
export GCP_REGION=us-central1
```

## §1 Provision a new environment

For a brand-new GCP project (e.g. `medication-companion-prod`).

1. **Create + bill the project** (Console or `gcloud projects create`, link a billing account).
2. **Enable Firebase** on the project (Firebase Console → Add project → reuse GCP project). Turn on Email/Password auth.
3. **Enable Firestore** (Firebase Console → Firestore → Create database): **Native mode**, database ID **`(default)`**, location **`us-central1`**. Default private rules (no client read/write) are correct — job state is backend-only; Flutter polls `GET /jobs/{id}`.
4. **Generate Flutter Firebase config** for this env:
   ```bash
   cd frontend && flutterfire configure --project=$GCP_PROJECT
   ```
5. **Apply Terraform** (creates app SA, buckets, broker + worker Cloud Run skeletons, Pub/Sub topics, Artifact Registry).
   - Single-project dev: `make infra-apply GCP_PROJECT=$GCP_PROJECT`
   - Multi-env (cicd module): `cd deployment/terraform/cicd && terraform apply` with `prod_project_id` / `staging_project_id` tfvars.
6. **Upload `drugs.db`** once:
   ```bash
   gcloud storage cp data/drugs.db gs://$GCP_PROJECT-uploads/artifacts/drugs.db
   ```
6. **BigQuery eval audit table** (LLM-as-Judge scores from production runs).
   Not created by Terraform today — run once per new GCP project:
   ```bash
   GCP_PROJECT=$GCP_PROJECT ./scripts/setup_eval_bigquery.sh
   ```
   Creates dataset `medication_companion` and table `eval_log`. Idempotent.
   Grants **project-level** `roles/bigquery.dataEditor` to **`medication-companion-app@…`**
   (the `agents-cli deploy --service-account` identity). Runtime code uses
   `google.auth.default()` as that SA — not the Reasoning Engine managed SA.
   Verify:
   ```bash
   bq query --use_legacy_sql=false \
     "SELECT COUNT(*) FROM \`${GCP_PROJECT}.medication_companion.eval_log\`"
   ```
   Without this step, deployed Agent Runtime logs
   `BigQuery write failed: … Dataset …:medication_companion` (404) or
   `Permission bigquery.tables.updateData denied` (403) after each successful
   prescription (pipeline still returns to the patient). The script grants
   `bigquery.dataEditor` on the dataset to `medication-companion-app@…` and
   the Reasoning Engine managed SA.
7. **Bootstrap GitHub Actions** (only if CI deploys this env): set repo vars + WIF via the `cicd` module's outputs.

## §2 Full backend deploy (Agent Runtime + auth broker)

Order matters — broker reads `AGENT_RUNTIME_RESOURCE` from
`deployment_metadata.json` produced by the Agent Runtime deploy.

```bash
# 1. Agent Runtime (ADK pipeline)
make deploy-prep    GCP_PROJECT=$GCP_PROJECT
make deploy         GCP_PROJECT=$GCP_PROJECT GCP_REGION=$GCP_REGION
make deploy-status  GCP_PROJECT=$GCP_PROJECT
make grant-tts-iam  GCP_PROJECT=$GCP_PROJECT     # first deploy only; idempotent

# 2. Auth broker (Cloud Run revision against the TF-managed service)
make deploy-auth-broker GCP_PROJECT=$GCP_PROJECT GCP_REGION=$GCP_REGION

# Convenience wrapper for both
make deploy-backend GCP_PROJECT=$GCP_PROJECT GCP_REGION=$GCP_REGION
```

Smoke-test the backend without Flutter (see [smoke_test_cheatsheet.md](smoke_test_cheatsheet.md) for all scenarios):

```bash
export RX_IMAGE=~/path/to/prescription.jpg   # or data/sample/prescription.jpg (local)

uv run python scripts/test_prescription.py "$RX_IMAGE" \
  --url https://$GCP_PROJECT.web.app \
  --token "$FIREBASE_ID_TOKEN"
```

## §2.1 Async prescription path (Pub/Sub + worker + Firestore)

**Agent Runtime redeploy is not required** for this feature. Async only changes
how the auth broker and worker invoke the **existing** Reasoning Engine
(`run_prescription_pipeline` → `streamQuery`). There are no changes under
`backend/agents/` or `backend/tools/` for Pub/Sub.

You need a **working Agent Runtime already deployed** (§2 step 1) so
`deployment_metadata.json` contains `remote_agent_runtime_id`. The worker and
broker only need that ID in env — not a new `make deploy`.

| Step | Command | Notes |
|------|---------|-------|
| 1. Infra (once) | `make infra-apply GCP_PROJECT=$GCP_PROJECT` | `pubsub.tf`: topic, push sub, worker skeleton, Firestore IAM |
| 2. Firestore (once) | Console: `(default)`, `us-central1`, Native | See §1 step 3 |
| 3. Broker + worker images | See below | No `make deploy` unless pipeline code changed |

**First-time async rollout** (Agent Runtime already live, sync path still works):

```bash
export GCP_PROJECT=medication-companion-dev
export GCP_REGION=us-central1

# Infra + Firestore (once)
make infra-apply GCP_PROJECT=$GCP_PROJECT

# Deploy broker (ASYNC_PRESCRIPTION=false — sync default) + worker
make deploy-async-backend GCP_PROJECT=$GCP_PROJECT GCP_REGION=$GCP_REGION
```

`deploy-async-backend` runs `deploy-auth-broker` then `deploy-prescription-worker`.
Both scripts read `AGENT_RUNTIME_RESOURCE` from `deployment_metadata.json`.

**Enable async responses** after smoke passes (`POST /prescription` → `202`, poll `GET /jobs/{id}`):

```bash
make deploy-auth-broker GCP_PROJECT=$GCP_PROJECT ASYNC_PRESCRIPTION=true
```

**After an Agent Runtime redeploy** (pipeline code changed — §4): run
`make deploy && make deploy-auth-broker` as today, **plus**
`make deploy-prescription-worker` so the worker gets the new runtime ID.

**Local dev** (no Firestore/Pub/Sub): `make local-auth-broker` with
`ASYNC_PRESCRIPTION=true JOB_STORE_BACKEND=memory PUBSUB_BACKEND=inline USE_LOCAL_RUNNER=true`.

CI does not deploy the worker yet — manual steps above until cicd `pubsub.tf` lands.

## §3 Full frontend deploy (Flutter PWA + Firebase Hosting)

```bash
make deploy-frontend GCP_PROJECT=$GCP_PROJECT
# Equivalent to:
#   cd frontend && flutter build web --release \
#     --dart-define=API_BASE_URL=https://$GCP_PROJECT.web.app \
#     --dart-define=ENVIRONMENT=production
#   firebase deploy --only hosting --project $GCP_PROJECT
```

Requires [`firebase.json`](../firebase.json) rewrites to the auth broker (already in repo) and a non-stub
[`firebase_options.dart`](../frontend/lib/firebase_options.dart) (run `flutterfire configure` once per env).

## §4 Backend-only update (bug fix, new agent step, e.g. Q&A)

Pick the smallest command for what changed.

| Change scope | Commands |
|--------------|----------|
| Agent pipeline (`backend/agents/`, `backend/tools/`, `backend/policy/`) | `make deploy && make deploy-auth-broker` (+ `make deploy-prescription-worker` if async enabled) |
| Auth broker only (`backend/auth_broker/`) | `make deploy-auth-broker` |
| Async orchestration only (broker/worker, no pipeline change) | `make deploy-async-backend` — **no** `make deploy` |
| Both pipeline + broker | `make deploy-backend` |
| `drugs.db` / CSVs | Rebuild locally → `make deploy-prep && make deploy` |
| Infra (Pub/Sub, worker skeleton, IAM) | `make infra-apply` (single-project) or `terraform apply` in cicd — **not on every code push** |

The broker redeploy after an Agent Runtime update is required only when the
runtime resource ID changes (`deployment_metadata.json`). For pure pipeline
code edits with the same runtime ID, `make deploy` alone is sufficient.

## §5 Frontend-only update (UI, copy, language picker)

```bash
make deploy-frontend GCP_PROJECT=$GCP_PROJECT
```

No Agent Runtime or auth broker redeploy needed.

## §6 CI path (reference)

| Workflow | Trigger | What it deploys |
|----------|---------|-----------------|
| [`staging.yaml`](../.github/workflows/staging.yaml) | Push to `main` (paths: backend, frontend, deployment, firebase.json) | Agent Runtime → auth broker → Firebase Hosting → load test |
| [`deploy-to-prod.yaml`](../.github/workflows/deploy-to-prod.yaml) | Called by `staging.yaml` after success | Same sequence against the prod project (manual approval if configured) |
| [`ci.yml`](../.github/workflows/ci.yml) | Push / PR | Backend lint + tests, Flutter analyze + tests, shellcheck. **No deploy** (legacy `deploy.sh` removed). |

## §7 Environment variable quick reference

| Variable | Where set | Used by |
|----------|-----------|---------|
| `GCP_PROJECT` / `GCP_REGION` | Shell, Make, CI vars | All deploy commands |
| `GCS_BUCKET` | Terraform → Cloud Run env | Auth broker signed URLs |
| `AGENT_RUNTIME_RESOURCE` | `deployment_metadata.json` → broker + worker deploy scripts | Auth broker, prescription worker |
| `FIREBASE_PROJECT_ID` | Terraform → Cloud Run env | Auth broker CORS |
| `PUBSUB_TOPIC` | `deploy/auth_broker/deploy.sh` (default `prescription-jobs`) | Auth broker publish |
| `FIRESTORE_PROJECT` | Deploy scripts (default `$GCP_PROJECT`) | Auth broker + worker job store |
| `JOB_STORE_BACKEND` | Deploy scripts (`firestore` in prod) | Auth broker + worker |
| `ASYNC_PRESCRIPTION` | `deploy-auth-broker` (default `false`; `ASYNC_PRESCRIPTION=true` to cut over) | Auth broker — `202` vs sync `200` |
| `API_BASE_URL` | Flutter `--dart-define` | Flutter `ApiService` |
| `ENVIRONMENT` | Flutter `--dart-define` + broker env | Both (toggles dev bypass) |
| `BIGQUERY_DATASET` | Agent Runtime env (default `medication_companion`) | `backend/evaluation/llm_judge.py` → `eval_log` writes |
| `LOGS_BUCKET_NAME` | `make deploy` / CI (`{project}-medication-companion-logs`) | Prompt-response telemetry (`backend/app_utils/telemetry.py`) |
| `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` | `make deploy` / CI | `EVENT_ONLY` (dev/staging) or `NO_CONTENT` (prod) — see §7.1 |

### §7.1 Prompt-response logging (dev vs prod)

| Environment | Mode | What you get in Traces |
|-------------|------|------------------------|
| **Dev / staging** | `EVENT_ONLY` | Full prompts/responses in Inputs/Outputs; GCS `completions/` |
| **Prod (default)** | `NO_CONTENT` | Span DAG, latency, tokens — no prompt/response text |
| **Prod break-glass** | Temporarily `EVENT_ONLY` | One synthetic session, then revert |

**Manual deploy (Make):**

```bash
# Dev — default after this change
make deploy-backend GCP_PROJECT=medication-companion-dev

# Prod — always pass NO_CONTENT explicitly
make deploy-backend GCP_PROJECT=medication-companion-prod OTEL_GENAI_CAPTURE_MODE=NO_CONTENT
```

**Prod ad-hoc debug (synthetic Rx only):**

```bash
agents-cli deploy --project $PROD_PROJECT --region us-central1 \
  --update-env-vars="OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=EVENT_ONLY,LOGS_BUCKET_NAME=${PROD_PROJECT}-medication-companion-logs"
# run one test session → inspect Traces or gs://…/completions/
agents-cli deploy --project $PROD_PROJECT --region us-central1 \
  --update-env-vars="OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=NO_CONTENT,LOGS_BUCKET_NAME=${PROD_PROJECT}-medication-companion-logs"
```

Use committed fixtures (`data/sample/smoke_4drug_2interactions.png`), not real patient uploads. Optional: delete the session’s objects under `gs://…/completions/` after debugging.

## §8 Troubleshooting one-liners

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `infra-apply` fails: `gcp-sa-firebasehosting... does not exist` | Older Terraform tried to grant a non-existent Hosting service agent | Pull latest — that IAM binding was removed. Re-run `make infra-apply`. |
| `make deploy-status` fails: Reasoning Engine failed to update + `language_map.yaml` in stderr | Agent Runtime upload includes only `backend/`; `ContextResolver` imports need `specs/schemas/language_map.yaml` | `make deploy` (runs `deploy-prep`, copies YAML into `backend/specs/`). Unrelated to `MEMORY_BACKEND`. |
| Cloud Run: container failed to start on PORT 8080 | Startup import crash (check revision logs) | Common: `FileNotFoundError: .../specs/schemas/language_map.yaml` — rebuild broker image after `COPY specs` in Dockerfile. Re-run `make deploy-auth-broker`. |
| `docker push` 403 / `failed to fetch anonymous token` | Docker not authenticated to Artifact Registry | `gcloud auth login` then `gcloud auth configure-docker us-central1-docker.pkg.dev --quiet`; re-run `make deploy-auth-broker` only (skip full `deploy-backend`). |
| Browser → broker returns 403 | Auth broker still requires IAM auth (`--no-allow-unauthenticated`) | Firebase Hosting rewrites need public Cloud Run invoke. Re-run `make deploy-auth-broker` (uses `--allow-unauthenticated`; app still checks Firebase JWT). |
| `/upload-url` returns 500 "signing failed" | `app_sa` lacks `iam.serviceAccountTokenCreator` self-binding | `make grant-tts-iam` or re-run `terraform apply`. |
| `/prescription` returns 500 from Agent Runtime | Stale `AGENT_RUNTIME_RESOURCE` on broker or worker after a new `agents-cli deploy` | `make deploy-auth-broker` and `make deploy-prescription-worker` (re-read `deployment_metadata.json`). |
| `POST /prescription` returns `202` but job stays `pending` | Worker not deployed, Pub/Sub push 403, or missing IAM | `GCP_PROJECT=$GCP_PROJECT ./scripts/grant_pubsub_worker_push.sh`; check worker logs; DLQ topic `prescription-jobs-dlq`. Or `make infra-apply`. |
| `GET /jobs/{id}` JSON parse error via Hosting URL | `/jobs/**` rewrite not deployed | `firebase deploy --only hosting --project $GCP_PROJECT` (see `firebase.json`). |
| `GET /jobs/{id}` returns 404 | Wrong project, Firestore not enabled, or job owned by another patient | Confirm Firestore `(default)` in `us-central1`; JWT `patient_id` must match job doc. |
| Agent 5 TTS audio missing | `-re` SA lacks signBlob on first deploy in a project | `make grant-tts-iam GCP_PROJECT=$GCP_PROJECT`. |
| Flutter shows "Firebase not configured" | `firebase_options.dart` is still the stub | `cd frontend && flutterfire configure --project=$GCP_PROJECT`. |
| `BigQuery write failed: Dataset …:medication_companion` | Eval audit dataset not provisioned in this project | `GCP_PROJECT=$GCP_PROJECT ./scripts/setup_eval_bigquery.sh` (see §1 step 6). |
| `BigQuery write failed: … Permission bigquery.tables.updateData denied` | Deploy SA (`medication-companion-app@…`) lacks BQ insert IAM | `GCP_PROJECT=$GCP_PROJECT ./scripts/setup_eval_bigquery.sh` or `gcloud projects add-iam-policy-binding … --member=serviceAccount:medication-companion-app@… --role=roles/bigquery.dataEditor`. Or `terraform apply` (`app_sa_roles` includes `bigquery.dataEditor`). Re-run smoke. |
| `bq query … eval_log` returns blank / zero rows | Judge ran but inserts failed (403/404), or eval skipped (Gate 1) | Check Cloud Logging for `Pipeline eval complete` vs `BigQuery write failed`. Fix IAM/dataset, re-run smoke. |

For deeper investigation see [docs/forensic_prompts.md](forensic_prompts.md).
