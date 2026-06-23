#!/usr/bin/env bash
# deploy/auth_broker/deploy.sh
#
# Build, push, and deploy the auth broker container to an existing
# Terraform-managed Cloud Run service. Terraform owns the service skeleton,
# Artifact Registry repo, IAM, and static env vars (ENVIRONMENT, GCS_BUCKET,
# FIREBASE_PROJECT_ID). This script only updates:
#   - the container image
#   - AGENT_RUNTIME_RESOURCE env var (read from deployment_metadata.json)
#   - async prescription env vars (Pub/Sub + Firestore; ASYNC_PRESCRIPTION defaults false)
#
# Prerequisites:
#   - `terraform apply` ran (single-project: make infra-apply, or cicd module)
#   - `agents-cli deploy` ran, producing deployment_metadata.json
#   - `gcloud auth login` + `gcloud auth configure-docker <region>-docker.pkg.dev`
#
# Usage:
#   GCP_PROJECT=medication-companion-dev ./deploy/auth_broker/deploy.sh
#   GCP_PROJECT=... GCP_REGION=us-central1 IMAGE_TAG=v1.2.3 ./deploy.sh

set -euo pipefail

# ── Inputs ────────────────────────────────────────────────────────────────────
GCP_PROJECT="${GCP_PROJECT:?GCP_PROJECT env var is required (e.g. medication-companion-dev)}"
GCP_REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-medication-companion-broker}"
REPO_ID="${REPO_ID:-medication-companion-broker}"
APP_SA="${APP_SA:-medication-companion-app@${GCP_PROJECT}.iam.gserviceaccount.com}"
IMAGE_TAG="${IMAGE_TAG:-$(date -u +%Y%m%d-%H%M%S)}"
PUBSUB_TOPIC="${PUBSUB_TOPIC:-prescription-jobs}"
FIRESTORE_PROJECT="${FIRESTORE_PROJECT:-${GCP_PROJECT}}"
ASYNC_PRESCRIPTION="${ASYNC_PRESCRIPTION:-false}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
METADATA_FILE="${REPO_ROOT}/deployment_metadata.json"

# ── Resolve AGENT_RUNTIME_RESOURCE from agents-cli deploy output ──────────────
if [[ -n "${AGENT_RUNTIME_RESOURCE:-}" ]]; then
  echo "▶ Using AGENT_RUNTIME_RESOURCE from env"
elif [[ -f "${METADATA_FILE}" ]]; then
  AGENT_RUNTIME_RESOURCE="$(python3 -c "import json,sys; print(json.load(open('${METADATA_FILE}'))['remote_agent_runtime_id'])")"
  echo "▶ Resolved AGENT_RUNTIME_RESOURCE from ${METADATA_FILE}"
else
  echo "ERROR: AGENT_RUNTIME_RESOURCE not set and ${METADATA_FILE} missing." >&2
  echo "       Run \`make deploy\` first to produce deployment_metadata.json." >&2
  exit 1
fi

REGISTRY="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/${REPO_ID}"
IMAGE="${REGISTRY}/auth-broker:${IMAGE_TAG}"

echo "▶ Project        : ${GCP_PROJECT}"
echo "▶ Region         : ${GCP_REGION}"
echo "▶ Service        : ${SERVICE_NAME}"
echo "▶ Image          : ${IMAGE}"
echo "▶ Service account: ${APP_SA}"
echo "▶ Runtime        : ${AGENT_RUNTIME_RESOURCE}"
echo "▶ Async flag     : ${ASYNC_PRESCRIPTION}"
echo "▶ Pub/Sub topic  : ${PUBSUB_TOPIC}"
echo "▶ Firestore      : ${FIRESTORE_PROJECT}"

# ── Build + push image ────────────────────────────────────────────────────────
echo "▶ Configuring Docker for Artifact Registry..."
gcloud auth configure-docker "${GCP_REGION}-docker.pkg.dev" --quiet

echo "▶ Building image..."
docker build \
  --platform=linux/amd64 \
  -f "${REPO_ROOT}/deploy/auth_broker/Dockerfile" \
  -t "${IMAGE}" \
  "${REPO_ROOT}"

echo "▶ Pushing image..."
docker push "${IMAGE}"

# ── Update Cloud Run revision ─────────────────────────────────────────────────
# Service skeleton (app_sa, static env vars) is owned by Terraform. We only set
# --image and the dynamic env var here.
#
# --allow-unauthenticated is required for Firebase Hosting rewrites: Hosting
# proxies browser requests to Cloud Run without an IAM identity token. Sensitive
# routes still verify Firebase JWT in auth_broker/auth.py.
echo "▶ Updating Cloud Run service..."
gcloud run deploy "${SERVICE_NAME}" \
  --project="${GCP_PROJECT}" \
  --region="${GCP_REGION}" \
  --image="${IMAGE}" \
  --service-account="${APP_SA}" \
  --allow-unauthenticated \
  --update-env-vars="AGENT_RUNTIME_RESOURCE=${AGENT_RUNTIME_RESOURCE},GOOGLE_CLOUD_PROJECT=${GCP_PROJECT},PUBSUB_TOPIC=${PUBSUB_TOPIC},FIRESTORE_PROJECT=${FIRESTORE_PROJECT},JOB_STORE_BACKEND=firestore,ASYNC_PRESCRIPTION=${ASYNC_PRESCRIPTION}" \
  --quiet

SERVICE_URL="$(gcloud run services describe "${SERVICE_NAME}" \
  --project="${GCP_PROJECT}" --region="${GCP_REGION}" \
  --format='value(status.url)')"

echo
echo "✓ Auth broker deployed: ${SERVICE_URL}"
echo "  (Browsers must reach it via Firebase Hosting rewrites — service is private.)"
