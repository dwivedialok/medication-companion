#!/usr/bin/env bash
# Grant IAM so Pub/Sub push (OIDC as app_sa) can invoke the prescription worker.
#
# Required when async prescriptions stay pending and worker logs show 403:
#   "The IAM principal lacks {run.routes.invoke} permission"
#
# Idempotent. Prefer `make infra-apply` long-term (pubsub.tf owns these bindings).
set -euo pipefail

GCP_PROJECT="${GCP_PROJECT:?Set GCP_PROJECT}"
GCP_REGION="${GCP_REGION:-us-central1}"
WORKER_SERVICE="${WORKER_SERVICE:-medication-companion-prescription-worker}"
APP_SA="${APP_SA:-medication-companion-app@${GCP_PROJECT}.iam.gserviceaccount.com}"

PROJECT_NUMBER="$(gcloud projects describe "${GCP_PROJECT}" --format='value(projectNumber)')"
PUBSUB_SA="service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com"

echo "▶ Grant run.invoker on ${WORKER_SERVICE} to ${APP_SA} (OIDC push identity)..."
gcloud run services add-iam-policy-binding "${WORKER_SERVICE}" \
  --project="${GCP_PROJECT}" \
  --region="${GCP_REGION}" \
  --member="serviceAccount:${APP_SA}" \
  --role=roles/run.invoker \
  --quiet

echo "▶ Grant Pub/Sub SA token creator on ${APP_SA} (mint OIDC for push)..."
gcloud iam service-accounts add-iam-policy-binding "${APP_SA}" \
  --project="${GCP_PROJECT}" \
  --member="serviceAccount:${PUBSUB_SA}" \
  --role=roles/iam.serviceAccountTokenCreator \
  --quiet

echo "✓ Pub/Sub → worker push IAM configured"
