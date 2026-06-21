# Deployment runbook

Operational cheat sheet for Medication Companion. One command per scenario —
no narrative. For architecture, see [AGENTS.md](../AGENTS.md) and
[deploy/auth_broker/README.md](../deploy/auth_broker/README.md).

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
6. **Bootstrap GitHub Actions** (only if CI deploys this env): set repo vars + WIF via the `cicd` module's outputs.

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

Smoke-test the backend without Flutter:

```bash
uv run python scripts/test_prescription.py data/sample/prescription.jpg \
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

## §8 Troubleshooting one-liners

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `infra-apply` fails: `gcp-sa-firebasehosting... does not exist` | Older Terraform tried to grant a non-existent Hosting service agent | Pull latest — that IAM binding was removed. Re-run `make infra-apply`. |
| Cloud Run: container failed to start on PORT 8080 | Startup import crash (check revision logs) | Common: `FileNotFoundError: .../specs/schemas/language_map.yaml` — rebuild broker image after `COPY specs` in Dockerfile. Re-run `make deploy-auth-broker`. |
| `docker push` 403 / `failed to fetch anonymous token` | Docker not authenticated to Artifact Registry | `gcloud auth login` then `gcloud auth configure-docker us-central1-docker.pkg.dev --quiet`; re-run `make deploy-auth-broker` only (skip full `deploy-backend`). |
| Browser → broker returns 403 | Auth broker still requires IAM auth (`--no-allow-unauthenticated`) | Firebase Hosting rewrites need public Cloud Run invoke. Re-run `make deploy-auth-broker` (uses `--allow-unauthenticated`; app still checks Firebase JWT). |
| `/upload-url` returns 500 "signing failed" | `app_sa` lacks `iam.serviceAccountTokenCreator` self-binding | `make grant-tts-iam` or re-run `terraform apply`. |
| `/prescription` returns 500 from Agent Runtime | Stale `AGENT_RUNTIME_RESOURCE` on broker after a new `agents-cli deploy` | `make deploy-auth-broker` (re-reads `deployment_metadata.json`). |
| Agent 5 TTS audio missing | `-re` SA lacks signBlob on first deploy in a project | `make grant-tts-iam GCP_PROJECT=$GCP_PROJECT`. |
| Flutter shows "Firebase not configured" | `firebase_options.dart` is still the stub | `cd frontend && flutterfire configure --project=$GCP_PROJECT`. |

For deeper investigation see [docs/forensic_prompts.md](forensic_prompts.md).
