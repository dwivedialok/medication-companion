#!/usr/bin/env bash
# =============================================================================
# scripts/setup_gcp.sh
# Pre-Terraform bootstrap for a fresh Medication Companion GCP project.
#
# Source of truth for infra = Terraform under deployment/terraform/.
# This script ONLY handles things Terraform cannot reasonably bootstrap itself:
#   - enabling the APIs Terraform needs before it can run
#   - Firestore / Firebase (console steps — not in Terraform yet)
#
# NOT handled here (see Makefile / Terraform instead):
#   - GCS buckets, IAM, telemetry, APIs     → make infra-apply (Terraform)
#   - Dev user uploads-bucket access        → Terraform dev_deployer_email in env.tfvars
#   - Agent code + DRUGS_DB_GCS_URI         → make deploy
#   - TTS signBlob on Reasoning Engine SA   → make post-deploy (auto after deploy)
#
# Usage:
#   ./scripts/setup_gcp.sh [--project PROJECT_ID] [--region REGION]
#
# Prerequisites:
#   - gcloud CLI installed and authenticated (gcloud auth login)
#   - Billing enabled on the project
#   - Owner on the project (needed to enable APIs)
# =============================================================================
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${GCP_REGION:-us-central1}"

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
echo "║  Medication Companion — pre-Terraform bootstrap          ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  Project : $PROJECT_ID"
echo "║  Region  : $REGION"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

gcloud config set project "$PROJECT_ID"

# ── 1. Enable APIs Terraform needs to run ─────────────────────────────────────
echo "▶ Enabling bootstrap APIs..."
gcloud services enable \
  cloudresourcemanager.googleapis.com \
  serviceusage.googleapis.com \
  iam.googleapis.com \
  --project="$PROJECT_ID"
echo "✓ Bootstrap APIs enabled"

# ── 2. Firebase / Firestore (manual steps — not in Terraform yet) ─────────────
echo ""
echo "▶ Firebase setup (manual — Firebase project linking is not in Terraform):"
echo "  1. Go to https://console.firebase.google.com"
echo "  2. Add Firebase to project: $PROJECT_ID"
echo "  3. Enable Authentication → Email/Password"
echo "  4. Enable Firestore Database (Native mode, region: $REGION)"
echo "  5. Run: firebase use $PROJECT_ID"
echo "  6. Run: firebase deploy --only firestore:rules"

# ── 3. Next steps ─────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Bootstrap complete. Next steps:                         ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  1. Complete Firebase setup (see above)                  ║"
echo "║  2. Set dev_deployer_email in                            ║"
echo "║     deployment/terraform/single-project/vars/env.tfvars  ║"
echo "║     (your Gmail — for make deploy drugs.db upload)         ║"
echo "║  3. make infra-apply                                     ║"
echo "║  4. Set AGENT_RUNTIME_RESOURCE in .env (from agents-cli    ║"
echo "║     deploy output or existing engine ID)                 ║"
echo "║  5. make deploy   (also runs post-deploy / grant-tts-iam)║"
echo "╚══════════════════════════════════════════════════════════╝"
