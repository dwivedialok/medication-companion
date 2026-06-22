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
3. **Generate Flutter Firebase config** for this env:
   ```bash
   cd frontend && flutterfire configure --project=$GCP_PROJECT
   ```
4. **Apply Terraform** (creates app SA, buckets, broker Cloud Run skeleton, Artifact Registry).
   - Single-project dev: `make infra-apply GCP_PROJECT=$GCP_PROJECT`
   - Multi-env (cicd module): `cd deployment/terraform/cicd && terraform apply` with `prod_project_id` / `staging_project_id` tfvars.
5. **Upload `drugs.db`** once:
   ```bash
   gcloud storage cp data/drugs.db gs://$GCP_PROJECT-uploads/artifacts/drugs.db
   ```
6. **BigQuery eval audit table** (async LLM-as-Judge scores from production runs).
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
| Agent pipeline (`backend/agents/`, `backend/tools/`, `backend/policy/`) | `make deploy && make deploy-auth-broker` |
| Auth broker only (`backend/auth_broker/`) | `make deploy-auth-broker` |
| Both | `make deploy-backend` |
| `drugs.db` / CSVs | Rebuild locally → `make deploy-prep && make deploy` |
| Infra (new bucket, IAM, broker env var) | `make infra-apply` (single-project) or `terraform apply` in cicd — **not on every code push** |

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
| `AGENT_RUNTIME_RESOURCE` | `deployment_metadata.json` → `gcloud run deploy --update-env-vars` | Auth broker |
| `FIREBASE_PROJECT_ID` | Terraform → Cloud Run env | Auth broker CORS |
| `API_BASE_URL` | Flutter `--dart-define` | Flutter `ApiService` |
| `ENVIRONMENT` | Flutter `--dart-define` + broker env | Both (toggles dev bypass) |
| `BIGQUERY_DATASET` | Agent Runtime env (default `medication_companion`) | `backend/evaluation/llm_judge.py` → `eval_log` writes |
| `LOGS_BUCKET_NAME` | `make deploy` / CI (`{project}-medication-companion-logs`) | Prompt-response telemetry (`backend/app_utils/telemetry.py`) |

## §8 Troubleshooting one-liners

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `infra-apply` fails: `gcp-sa-firebasehosting... does not exist` | Older Terraform tried to grant a non-existent Hosting service agent | Pull latest — that IAM binding was removed. Re-run `make infra-apply`. |
| `make deploy-status` fails: Reasoning Engine failed to update + `language_map.yaml` in stderr | Agent Runtime upload includes only `backend/`; `ContextResolver` imports need `specs/schemas/language_map.yaml` | `make deploy` (runs `deploy-prep`, copies YAML into `backend/specs/`). Unrelated to `MEMORY_BACKEND`. |
| Cloud Run: container failed to start on PORT 8080 | Startup import crash (check revision logs) | Common: `FileNotFoundError: .../specs/schemas/language_map.yaml` — rebuild broker image after `COPY specs` in Dockerfile. Re-run `make deploy-auth-broker`. |
| `docker push` 403 / `failed to fetch anonymous token` | Docker not authenticated to Artifact Registry | `gcloud auth login` then `gcloud auth configure-docker us-central1-docker.pkg.dev --quiet`; re-run `make deploy-auth-broker` only (skip full `deploy-backend`). |
| Browser → broker returns 403 | Auth broker still requires IAM auth (`--no-allow-unauthenticated`) | Firebase Hosting rewrites need public Cloud Run invoke. Re-run `make deploy-auth-broker` (uses `--allow-unauthenticated`; app still checks Firebase JWT). |
| `/upload-url` returns 500 "signing failed" | `app_sa` lacks `iam.serviceAccountTokenCreator` self-binding | `make grant-tts-iam` or re-run `terraform apply`. |
| `/prescription` returns 500 from Agent Runtime | Stale `AGENT_RUNTIME_RESOURCE` on broker after a new `agents-cli deploy` | `make deploy-auth-broker` (re-reads `deployment_metadata.json`). |
| Agent 5 TTS audio missing | `-re` SA lacks signBlob on first deploy in a project | `make grant-tts-iam GCP_PROJECT=$GCP_PROJECT`. |
| Flutter shows "Firebase not configured" | `firebase_options.dart` is still the stub | `cd frontend && flutterfire configure --project=$GCP_PROJECT`. |
| `BigQuery write failed: Dataset …:medication_companion` | Eval audit dataset not provisioned in this project | `GCP_PROJECT=$GCP_PROJECT ./scripts/setup_eval_bigquery.sh` (see §1 step 6). |
| `BigQuery write failed: … Permission bigquery.tables.updateData denied` | Deploy SA (`medication-companion-app@…`) lacks BQ insert IAM | `GCP_PROJECT=$GCP_PROJECT ./scripts/setup_eval_bigquery.sh` or `gcloud projects add-iam-policy-binding … --member=serviceAccount:medication-companion-app@… --role=roles/bigquery.dataEditor`. Or `terraform apply` (`app_sa_roles` includes `bigquery.dataEditor`). Re-run smoke. |
| `bq query … eval_log` returns blank / zero rows | Judge ran but inserts failed (403/404), or eval skipped (Gate 1) | Check Cloud Logging for `Pipeline eval complete` vs `BigQuery write failed`. Fix IAM/dataset, re-run smoke. |

For deeper investigation see [docs/forensic_prompts.md](forensic_prompts.md).
