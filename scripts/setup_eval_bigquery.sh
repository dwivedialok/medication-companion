#!/usr/bin/env bash
# Create BigQuery dataset + eval_log table for async LLM-as-Judge scores,
# and grant insert permission to Agent Runtime.
#
# Agent Runtime runs as medication-companion-app@PROJECT (see Makefile APP_SA /
# agents-cli deploy --service-account), NOT the Reasoning Engine managed SA.
# google.auth.default() inside llm_judge.py uses that deploy SA.
#
# Usage:
#   GCP_PROJECT=medication-companion-dev ./scripts/setup_eval_bigquery.sh
set -euo pipefail

PROJECT="${GCP_PROJECT:-medication-companion-dev}"
DATASET="${BIGQUERY_DATASET:-medication_companion}"
DATASET_ID="${PROJECT}:${DATASET}"
APP_SA="${APP_SA:-medication-companion-app@${PROJECT}.iam.gserviceaccount.com}"

if ! bq --project_id="${PROJECT}" show "${DATASET_ID}" >/dev/null 2>&1; then
  echo "Creating dataset ${DATASET_ID}..."
  bq --project_id="${PROJECT}" mk --dataset \
    --location=us-central1 \
    --description="Medication Companion eval audit trail" \
    "${DATASET_ID}"
else
  echo "Dataset ${DATASET_ID} already exists."
fi

if ! bq --project_id="${PROJECT}" show "${DATASET_ID}.eval_log" >/dev/null 2>&1; then
  echo "Creating table ${DATASET_ID}.eval_log..."
  bq --project_id="${PROJECT}" mk --table \
    "${DATASET_ID}.eval_log" \
    session_id:STRING,timestamp:TIMESTAMP,patient_id:STRING,safety_score:INTEGER,clarity_score:INTEGER,flags:STRING,agent_versions:STRING,model_version:STRING
else
  echo "Table ${DATASET_ID}.eval_log already exists."
fi

echo "Granting roles/bigquery.dataEditor on project ${PROJECT} to ${APP_SA}..."
echo "(This is the agents-cli deploy --service-account identity.)"
gcloud projects add-iam-policy-binding "${PROJECT}" \
  --member="serviceAccount:${APP_SA}" \
  --role="roles/bigquery.dataEditor" \
  --condition=None

echo "Done. Verify after the next smoke test:"
echo "  bq query --use_legacy_sql=false --format=pretty 'SELECT COUNT(*) FROM \`${PROJECT}.${DATASET}.eval_log\`'"
echo ""
echo "Cloud Logging should show Pipeline eval complete without BigQuery write failed."
