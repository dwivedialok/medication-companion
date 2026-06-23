#!/usr/bin/env bash
# deploy/workers/deploy.sh — build and deploy prescription worker to Cloud Run.
#
# Terraform owns the service skeleton (Pub/Sub push target, static env vars).
# This script updates the container image and runtime env vars the worker needs
# to call the existing Agent Runtime and Firestore job store.
#
# Prerequisites:
#   - `make infra-apply` (pubsub.tf — worker service + push subscription)
#   - Firestore Native `(default)` in us-central1
#   - `agents-cli deploy` already ran (broker uses the same Reasoning Engine)
#   - `deployment_metadata.json` present OR AGENT_RUNTIME_RESOURCE exported
#
# Usage:
#   GCP_PROJECT=medication-companion-dev ./deploy/workers/deploy.sh
#   GCP_PROJECT=... AGENT_RUNTIME_RESOURCE=projects/.../reasoningEngines/... ./deploy.sh

set -euo pipefail

GCP_PROJECT="${GCP_PROJECT:?GCP_PROJECT env var is required}"
GCP_REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-medication-companion-prescription-worker}"
REPO_ID="${REPO_ID:-medication-companion-broker}"
APP_SA="${APP_SA:-medication-companion-app@${GCP_PROJECT}.iam.gserviceaccount.com}"
IMAGE_TAG="${IMAGE_TAG:-$(date -u +%Y%m%d-%H%M%S)}"
GCS_BUCKET="${GCS_BUCKET:-medication-companion-uploads}"
FIRESTORE_PROJECT="${FIRESTORE_PROJECT:-${GCP_PROJECT}}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
METADATA_FILE="${REPO_ROOT}/deployment_metadata.json"

if [[ -n "${AGENT_RUNTIME_RESOURCE:-}" ]]; then
  echo "▶ Using AGENT_RUNTIME_RESOURCE from env"
elif [[ -f "${METADATA_FILE}" ]]; then
  AGENT_RUNTIME_RESOURCE="$(python3 -c "import json,sys; print(json.load(open('${METADATA_FILE}'))['remote_agent_runtime_id'])")"
  echo "▶ Resolved AGENT_RUNTIME_RESOURCE from ${METADATA_FILE}"
else
  echo "ERROR: AGENT_RUNTIME_RESOURCE not set and ${METADATA_FILE} missing." >&2
  echo "       Run \`make deploy\` once (or export AGENT_RUNTIME_RESOURCE) — no new" >&2
  echo "       Agent Runtime deploy is required for async unless the runtime ID changed." >&2
  exit 1
fi

REGISTRY="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/${REPO_ID}"
IMAGE="${REGISTRY}/prescription-worker:${IMAGE_TAG}"

echo "▶ Project        : ${GCP_PROJECT}"
echo "▶ Region         : ${GCP_REGION}"
echo "▶ Service        : ${SERVICE_NAME}"
echo "▶ Image          : ${IMAGE}"
echo "▶ Service account: ${APP_SA}"
echo "▶ Runtime        : ${AGENT_RUNTIME_RESOURCE}"
echo "▶ GCS bucket     : ${GCS_BUCKET}"
echo "▶ Firestore      : ${FIRESTORE_PROJECT}"

echo "▶ Building prescription worker image..."
gcloud auth configure-docker "${GCP_REGION}-docker.pkg.dev" --quiet
docker build --platform=linux/amd64 -f "${REPO_ROOT}/deploy/workers/Dockerfile" -t "${IMAGE}" "${REPO_ROOT}"
docker push "${IMAGE}"

echo "▶ Deploying ${SERVICE_NAME}..."
gcloud run deploy "${SERVICE_NAME}" \
  --project="${GCP_PROJECT}" \
  --region="${GCP_REGION}" \
  --image="${IMAGE}" \
  --service-account="${APP_SA}" \
  --no-allow-unauthenticated \
  --update-env-vars="AGENT_RUNTIME_RESOURCE=${AGENT_RUNTIME_RESOURCE},GCS_BUCKET=${GCS_BUCKET},FIRESTORE_PROJECT=${FIRESTORE_PROJECT},JOB_STORE_BACKEND=firestore,ENVIRONMENT=production" \
  --quiet

echo "✓ Prescription worker deployed"
