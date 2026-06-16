#!/usr/bin/env bash
# =============================================================================
# deploy/deploy.sh
# Deploy Medication Companion to GCP.
# Deploys: Agent 5 A2A service → Main service (Agents 1-4) → Flutter PWA
#
# Usage:
#   ./deploy/deploy.sh [--project PROJECT_ID] [--region REGION] [--env ENV]
#
# Prerequisites:
#   - setup_gcp.sh has been run
#   - .env.production exists (copy from .env.example)
#   - Firebase CLI installed and authenticated
#   - Flutter SDK installed
# =============================================================================
set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
PROJECT_ID="${GCP_PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${GCP_REGION:-us-central1}"
ENV="${DEPLOY_ENV:-production}"
GCS_BUCKET="${GCS_BUCKET_NAME:-medication-companion-uploads}"
SA_EMAIL="${SERVICE_ACCOUNT_NAME:-medication-companion-sa}@${PROJECT_ID}.iam.gserviceaccount.com"
IMAGE_REPO="${REGION}-docker.pkg.dev/${PROJECT_ID}/medication-companion"
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "local")
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
IMAGE_TAG="${GIT_SHA}-${TIMESTAMP}"

# ── Argument parsing ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    --project) PROJECT_ID="$2"; shift 2 ;;
    --region)  REGION="$2";     shift 2 ;;
    --env)     ENV="$2";        shift 2 ;;
    *)         echo "Unknown flag: $1"; exit 1 ;;
  esac
done

# ── Load environment variables ────────────────────────────────────────────────
ENV_FILE=".env.${ENV}"
if [[ -f "$ENV_FILE" ]]; then
  echo "Loading environment from $ENV_FILE..."
  set -a; source "$ENV_FILE"; set +a
else
  echo "WARNING: $ENV_FILE not found. Using environment variables only."
fi

AGENT_RUNTIME_ID="${AGENT_RUNTIME_ID:-}"
if [[ -z "$AGENT_RUNTIME_ID" ]]; then
  echo "ERROR: AGENT_RUNTIME_ID is required. Set it in $ENV_FILE."
  exit 1
fi

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Medication Companion — Deploy                           ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  Project   : $PROJECT_ID"
echo "║  Region    : $REGION"
echo "║  Env       : $ENV"
echo "║  Image tag : $IMAGE_TAG"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

gcloud config set project "$PROJECT_ID"

# ── Authenticate Docker to Artifact Registry ──────────────────────────────────
echo "▶ Configuring Docker auth..."
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

# ── Build and push: Agent 5 A2A image ─────────────────────────────────────────
echo "▶ Building Agent 5 (A2A localisation service)..."
A2A_IMAGE="${IMAGE_REPO}/a2a:${IMAGE_TAG}"
docker build \
  --file backend/Dockerfile.a2a \
  --tag "$A2A_IMAGE" \
  --build-arg BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --build-arg GIT_SHA="$GIT_SHA" \
  ./backend
docker push "$A2A_IMAGE"
echo "✓ A2A image pushed: $A2A_IMAGE"

# ── Deploy Agent 5 A2A service ────────────────────────────────────────────────
echo "▶ Deploying medication-companion-a2a..."
gcloud run deploy medication-companion-a2a \
  --image="$A2A_IMAGE" \
  --region="$REGION" \
  --service-account="$SA_EMAIL" \
  --no-allow-unauthenticated \
  --memory=1Gi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=10 \
  --timeout=120 \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION},GCS_BUCKET=${GCS_BUCKET},GEMINI_MODEL=${GEMINI_MODEL:-gemini-2.0-flash},ENVIRONMENT=${ENV},LOG_LEVEL=INFO" \
  --labels="app=medication-companion,component=a2a,git-sha=${GIT_SHA}" \
  --quiet

A2A_URL=$(gcloud run services describe medication-companion-a2a \
  --region="$REGION" --format='value(status.url)')
echo "✓ A2A service deployed: $A2A_URL"

# ── Build and push: Main service image ────────────────────────────────────────
echo "▶ Building main service (Agents 1-4)..."
MAIN_IMAGE="${IMAGE_REPO}/main:${IMAGE_TAG}"
docker build \
  --file backend/Dockerfile \
  --tag "$MAIN_IMAGE" \
  --build-arg BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --build-arg GIT_SHA="$GIT_SHA" \
  ./backend
docker push "$MAIN_IMAGE"
echo "✓ Main image pushed: $MAIN_IMAGE"

# ── Deploy main service ───────────────────────────────────────────────────────
echo "▶ Deploying medication-companion (main)..."
gcloud run deploy medication-companion \
  --image="$MAIN_IMAGE" \
  --region="$REGION" \
  --service-account="$SA_EMAIL" \
  --no-allow-unauthenticated \
  --memory=2Gi \
  --cpu=2 \
  --min-instances=0 \
  --max-instances=20 \
  --timeout=120 \
  --concurrency=10 \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION},AGENT_RUNTIME_ID=${AGENT_RUNTIME_ID},GCS_BUCKET=${GCS_BUCKET},A2A_AGENT5_URL=${A2A_URL},GEMINI_MODEL=${GEMINI_MODEL:-gemini-2.0-flash},FIREBASE_PROJECT_ID=${PROJECT_ID},BIGQUERY_DATASET=medication_companion,MEMORY_BACKEND=vertex,ENVIRONMENT=${ENV},LOG_LEVEL=INFO" \
  --labels="app=medication-companion,component=main,git-sha=${GIT_SHA}" \
  --quiet

MAIN_URL=$(gcloud run services describe medication-companion \
  --region="$REGION" --format='value(status.url)')
echo "✓ Main service deployed: $MAIN_URL"

# ── Build and deploy Flutter PWA ──────────────────────────────────────────────
echo "▶ Building Flutter PWA..."
cd frontend

# Inject the backend URL into the Flutter build
flutter build web --release \
  --dart-define=API_BASE_URL="$MAIN_URL" \
  --dart-define=ENVIRONMENT="$ENV"

echo "▶ Deploying to Firebase Hosting..."
firebase deploy --only hosting --project="$PROJECT_ID" --non-interactive
cd ..

HOSTING_URL="https://${PROJECT_ID}.web.app"
echo "✓ PWA deployed: $HOSTING_URL"

# ── Output deployment summary ─────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Deployment complete ✓                                   ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  PWA (patient app) : $HOSTING_URL"
echo "║  Main API          : $MAIN_URL"
echo "║  A2A service       : $A2A_URL"
echo "║  Image tag         : $IMAGE_TAG"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "Verify health:"
echo "  curl ${MAIN_URL}/health"
echo "  curl ${A2A_URL}/health"
