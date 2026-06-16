#!/usr/bin/env bash
# =============================================================================
# scripts/setup_gcp.sh
# One-time GCP project setup for Medication Companion.
# Run this ONCE before deploying. Idempotent — safe to re-run.
#
# Usage:
#   ./scripts/setup_gcp.sh [--project PROJECT_ID] [--region REGION]
#
# Prerequisites:
#   - gcloud CLI installed and authenticated (gcloud auth login)
#   - Billing enabled on the project
#   - Owner or Editor + required role grants
# =============================================================================
set -euo pipefail

# ── Defaults (override via flags or environment) ──────────────────────────────
PROJECT_ID="${GCP_PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${GCP_REGION:-us-central1}"
GCS_BUCKET="${GCS_BUCKET_NAME:-medication-companion-uploads}"
BQ_DATASET="medication_companion"
SERVICE_ACCOUNT_NAME="medication-companion-sa"
AGENT_RUNTIME_NAME="medication-companion-runtime"

# ── Argument parsing ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    --project) PROJECT_ID="$2"; shift 2 ;;
    --region)  REGION="$2";     shift 2 ;;
    *)         echo "Unknown flag: $1"; exit 1 ;;
  esac
done

if [[ -z "$PROJECT_ID" ]]; then
  echo "ERROR: No project ID set. Pass --project PROJECT_ID or run 'gcloud config set project PROJECT_ID'"
  exit 1
fi

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Medication Companion — GCP Setup                        ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  Project : $PROJECT_ID"
echo "║  Region  : $REGION"
echo "║  Bucket  : $GCS_BUCKET"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

gcloud config set project "$PROJECT_ID"

# ── 1. Enable required APIs ───────────────────────────────────────────────────
echo "▶ Enabling GCP APIs..."
gcloud services enable \
  aiplatform.googleapis.com \
  run.googleapis.com \
  storage.googleapis.com \
  texttospeech.googleapis.com \
  bigquery.googleapis.com \
  cloudtrace.googleapis.com \
  logging.googleapis.com \
  secretmanager.googleapis.com \
  firebase.googleapis.com \
  firestore.googleapis.com \
  iam.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  --project="$PROJECT_ID"
echo "✓ APIs enabled"

# ── 2. Service account ────────────────────────────────────────────────────────
echo "▶ Creating service account: $SERVICE_ACCOUNT_NAME..."
SA_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud iam service-accounts create "$SERVICE_ACCOUNT_NAME" \
  --display-name="Medication Companion Runtime SA" \
  --project="$PROJECT_ID" 2>/dev/null || echo "  (already exists)"

# Grant only the roles the service needs — principle of least privilege
ROLES=(
  "roles/aiplatform.user"          # Vertex AI Agent Engine
  "roles/storage.objectAdmin"      # GCS read/write for uploads + audio
  "roles/bigquery.dataEditor"      # Write eval logs
  "roles/bigquery.jobUser"         # Run BQ jobs
  "roles/cloudtrace.agent"         # Write traces
  "roles/logging.logWriter"        # Structured logging
  "roles/texttospeech.user"        # TTS API
  "roles/secretmanager.secretAccessor"  # Read secrets
)

for ROLE in "${ROLES[@]}"; do
  echo "  Granting $ROLE to $SA_EMAIL..."
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="$ROLE" \
    --condition=None \
    --quiet
done
echo "✓ Service account configured"

# ── 3. Artifact Registry (for Cloud Run container images) ─────────────────────
echo "▶ Creating Artifact Registry repository..."
gcloud artifacts repositories create medication-companion \
  --repository-format=docker \
  --location="$REGION" \
  --description="Medication Companion container images" \
  --project="$PROJECT_ID" 2>/dev/null || echo "  (already exists)"
echo "✓ Artifact Registry ready"

# ── 4. Cloud Storage bucket ───────────────────────────────────────────────────
echo "▶ Creating GCS bucket: gs://$GCS_BUCKET..."
gcloud storage buckets create "gs://$GCS_BUCKET" \
  --location="$REGION" \
  --uniform-bucket-level-access \
  --project="$PROJECT_ID" 2>/dev/null || echo "  (already exists)"

# CORS config for PWA uploads
cat > /tmp/cors.json << 'EOF'
[
  {
    "origin": ["*"],
    "method": ["GET", "PUT", "POST"],
    "responseHeader": ["Content-Type", "Authorization"],
    "maxAgeSeconds": 3600
  }
]
EOF
gcloud storage buckets update "gs://$GCS_BUCKET" --cors-file=/tmp/cors.json
rm /tmp/cors.json
echo "✓ GCS bucket ready"

# ── 5. BigQuery dataset + eval log table ──────────────────────────────────────
echo "▶ Creating BigQuery dataset and tables..."
bq --project_id="$PROJECT_ID" mk \
  --dataset \
  --location="$REGION" \
  --description="Medication Companion evaluation logs" \
  "${PROJECT_ID}:${BQ_DATASET}" 2>/dev/null || echo "  (dataset already exists)"

bq --project_id="$PROJECT_ID" mk \
  --table \
  --description="LLM-as-Judge evaluation scores per pipeline run" \
  "${PROJECT_ID}:${BQ_DATASET}.eval_log" \
  "session_id:STRING,timestamp:TIMESTAMP,patient_id:STRING,safety_score:INTEGER,clarity_score:INTEGER,flags:STRING,agent_versions:STRING,model_version:STRING" \
  2>/dev/null || echo "  (table already exists)"

bq --project_id="$PROJECT_ID" mk \
  --table \
  --description="Audit log of all pipeline runs" \
  "${PROJECT_ID}:${BQ_DATASET}.pipeline_audit" \
  "session_id:STRING,timestamp:TIMESTAMP,patient_id:STRING,drug_count:INTEGER,interaction_count:INTEGER,severity:STRING,pipeline_duration_ms:INTEGER,gate1_passed:BOOLEAN" \
  2>/dev/null || echo "  (table already exists)"
echo "✓ BigQuery configured"

# ── 6. Secret Manager — store sensitive config ────────────────────────────────
echo "▶ Configuring Secret Manager..."

create_secret_if_missing() {
  local SECRET_NAME="$1"
  local PLACEHOLDER="$2"
  if ! gcloud secrets describe "$SECRET_NAME" --project="$PROJECT_ID" &>/dev/null; then
    echo -n "$PLACEHOLDER" | gcloud secrets create "$SECRET_NAME" \
      --data-file=- \
      --replication-policy=automatic \
      --project="$PROJECT_ID"
    echo "  Created secret: $SECRET_NAME (update with real value before deploying)"
  else
    echo "  Exists: $SECRET_NAME"
  fi
}

create_secret_if_missing "medication-companion-gemini-key" "REPLACE_WITH_GEMINI_API_KEY"
echo "✓ Secrets configured"

# ── 7. Vertex AI Agent Engine runtime ─────────────────────────────────────────
echo "▶ Creating Vertex AI Agent Engine runtime..."
# Note: Agent Engine runtime creation may require the Vertex AI console
# or the aiplatform SDK. The deploy script will read AGENT_RUNTIME_ID
# from the environment. See docs/architecture.md for manual setup steps.
echo "  ⚠ Vertex AI Agent Engine runtime must be created via console or SDK."
echo "  Once created, set AGENT_RUNTIME_ID in your .env.production file."
echo "  See: https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/set-up"

# ── 8. Firebase project link ──────────────────────────────────────────────────
echo ""
echo "▶ Firebase setup (manual steps required):"
echo "  1. Go to https://console.firebase.google.com"
echo "  2. Add Firebase to project: $PROJECT_ID"
echo "  3. Enable Authentication → Email/Password"
echo "  4. Enable Firestore Database (Native mode, region: $REGION)"
echo "  5. Run: firebase use $PROJECT_ID"
echo "  6. Run: firebase deploy --only firestore:rules"

# ── 9. Output summary ─────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Setup complete. Next steps:                             ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  1. Complete Firebase setup (see above)                  ║"
echo "║  2. Create Vertex AI Agent Engine runtime                ║"
echo "║  3. Copy .env.example → .env.production, fill values     ║"
echo "║  4. Run: ./deploy/deploy.sh                              ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "Service Account: $SA_EMAIL"
echo "GCS Bucket:      gs://$GCS_BUCKET"
echo "BQ Dataset:      ${PROJECT_ID}:${BQ_DATASET}"
