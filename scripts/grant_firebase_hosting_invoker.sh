#!/usr/bin/env bash
# Legacy helper — Firebase Hosting rewrites do NOT invoke Cloud Run via
# gcp-sa-firebasehosting. Google documents deploying the target service with
# --allow-unauthenticated and enforcing Firebase JWT in application code instead.
#
# Kept as a no-op with guidance so older runbooks/CI steps fail softly.
set -euo pipefail

: "${GCP_PROJECT:?Set GCP_PROJECT}"
GCP_REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="${AUTH_BROKER_SERVICE:-medication-companion-broker}"

if gcloud run services get-iam-policy "${SERVICE_NAME}" \
  --project="${GCP_PROJECT}" \
  --region="${GCP_REGION}" \
  --flatten="bindings[].members" \
  --filter="bindings.role:roles/run.invoker AND bindings.members:allUsers" \
  --format="value(bindings.members)" 2>/dev/null | grep -q allUsers; then
  echo "OK: ${SERVICE_NAME} already allows unauthenticated invoke (required for Hosting rewrites)."
  exit 0
fi

cat >&2 <<EOF
grant-hosting-invoker is obsolete: gcp-sa-firebasehosting is not used for Hosting → Cloud Run.

Redeploy the auth broker with public Cloud Run invoke (app still verifies Firebase JWT):

  make deploy-auth-broker GCP_PROJECT=${GCP_PROJECT} GCP_REGION=${GCP_REGION}

Or one-off:

  gcloud run services add-iam-policy-binding ${SERVICE_NAME} \\
    --project=${GCP_PROJECT} --region=${GCP_REGION} \\
    --member=allUsers --role=roles/run.invoker
EOF
exit 1
