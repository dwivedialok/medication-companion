.PHONY: test local-auth-broker auth-broker deploy deploy-dry-run deploy-status deploy-prep playground infra infra-apply post-deploy grant-tts-iam grant-hosting-invoker deploy-auth-broker deploy-prescription-worker deploy-async-backend deploy-backend deploy-frontend

test:
	uv run pytest

# Local HTTP token broker (Firebase JWT → GCS → Agent Runtime). Not Pub/Sub — that
# is a separate ambient-agent path for a later phase.
local-auth-broker:
	cd backend && uv run uvicorn auth_broker.main:app --reload --host 0.0.0.0 --port 8080

auth-broker: local-auth-broker

playground:
	agents-cli playground

GCP_PROJECT ?= medication-companion-dev
GCP_REGION ?= us-central1
GCS_BUCKET ?= medication-companion-uploads
LOGS_BUCKET_NAME ?= $(GCP_PROJECT)-medication-companion-logs
DRUGS_DB_GCS_URI ?= gs://$(GCS_BUCKET)/artifacts/drugs.db
# Run Agent Runtime as our own app SA (Terraform-managed) instead of the
# Google-managed Reasoning Engine SA. The -re SA cannot be IAM-bound by
# project owners (NOT_FOUND on add-iam-policy-binding), which breaks Agent 5
# TTS V4 signed URLs (requires signBlob). app_sa has the same roles via
# Terraform and supports a self-binding for signBlob.
APP_SA ?= medication-companion-app@$(GCP_PROJECT).iam.gserviceaccount.com
# Gemini API endpoint is set per-model in backend/llm_models.py (GlobalGemini),
# so we do NOT inject GOOGLE_CLOUD_LOCATION here — Agent Runtime will set it to
# the engine's regional host (us-central1) and that stays correct for everything
# except the Gemini API, which uses its own pinned global client.
# Cross-visit medication history uses VertexAiMemoryBankService on deployed Runtime.
# Local dev keeps MEMORY_BACKEND=local in .env (see .env.example).
# Prompt-response logging: EVENT_ONLY in dev/staging (Traces Inputs/Outputs);
# NO_CONTENT in prod (metadata only). Override: OTEL_GENAI_CAPTURE_MODE=NO_CONTENT
OTEL_GENAI_CAPTURE_MODE ?= EVENT_ONLY
DEPLOY_ENV_VARS ?= DRUGS_DB_GCS_URI=$(DRUGS_DB_GCS_URI),MEMORY_BACKEND=vertex,LOGS_BUCKET_NAME=$(LOGS_BUCKET_NAME),OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=$(OTEL_GENAI_CAPTURE_MODE)

# Agent Runtime inline upload is capped at 8 MB. backend/venv (~380 MB) must not
# exist. drugs.db (~54 MB) is uploaded to GCS; india_brands.csv is copied into
# backend/data/ so it ships inside the backend/ tarball.
deploy-prep:
	@if [ -d backend/venv ]; then \
		echo "ERROR: backend/venv exceeds Agent Runtime's 8 MB deploy limit."; \
		echo "  rm -rf backend/venv   # use repo-root .venv via: uv sync"; \
		exit 1; \
	fi
	mkdir -p backend/data backend/specs/schemas
	cp data/india_brands.csv backend/data/
	cp specs/schemas/language_map.yaml backend/specs/schemas/
	@if [ -f data/drugs.db ]; then \
		gcloud storage cp data/drugs.db $(DRUGS_DB_GCS_URI) --quiet; \
	fi

deploy-dry-run: deploy-prep
	agents-cli deploy --dry-run --no-confirm-project \
		--project $(GCP_PROJECT) --region $(GCP_REGION) \
		--service-account=$(APP_SA) \
		--update-env-vars="$(DEPLOY_ENV_VARS)"

deploy: deploy-prep
	agents-cli deploy --no-wait --no-confirm-project \
		--project $(GCP_PROJECT) --region $(GCP_REGION) \
		--service-account=$(APP_SA) \
		--update-env-vars="$(DEPLOY_ENV_VARS)"
	@$(MAKE) post-deploy

deploy-status:
	agents-cli deploy --status \
		--project $(GCP_PROJECT) --region $(GCP_REGION)

# Terraform plan only (safe preview). Apply with: make infra-apply
infra:
	agents-cli infra single-project

infra-apply:
	agents-cli infra single-project --apply

# Post-deploy hooks (idempotent).
post-deploy: grant-tts-iam

# Grant the app SA the ability to sign blobs as itself. Required for Agent 5
# (TTS) V4 GCS signed URLs and the auth broker's GCS signed PUT URLs.
#
# NOTE: This binding is now declared in Terraform
# (deployment/terraform/{single-project,cicd}/auth_broker.tf via
# google_service_account_iam_member.app_sa_signblob). This Make target stays
# as a recovery / first-time bootstrap helper for projects that pre-date the
# TF resource or where the binding has drifted. Safe to re-run any time.
grant-tts-iam:
	@echo "Granting roles/iam.serviceAccountTokenCreator self-binding to $(APP_SA)"; \
	echo "(Required for Agent 5 TTS V4 GCS signed URLs via IAM signBlob)"; \
	gcloud iam service-accounts add-iam-policy-binding "$(APP_SA)" \
		--project=$(GCP_PROJECT) \
		--member="serviceAccount:$(APP_SA)" \
		--role=roles/iam.serviceAccountTokenCreator --quiet

# Grant Firebase Hosting → auth broker run.invoker (legacy — see script header).
grant-hosting-invoker:
	chmod +x scripts/grant_firebase_hosting_invoker.sh
	GCP_PROJECT=$(GCP_PROJECT) GCP_REGION=$(GCP_REGION) \
		./scripts/grant_firebase_hosting_invoker.sh

# ── Auth broker (Cloud Run) ───────────────────────────────────────────────────
# Build, push, and update the broker revision. Terraform owns the service
# skeleton + IAM; this script sets AGENT_RUNTIME_RESOURCE and Pub/Sub env vars.
# /prescription is always async — broker enqueues to Pub/Sub, worker processes.
deploy-auth-broker:
	GCP_PROJECT=$(GCP_PROJECT) GCP_REGION=$(GCP_REGION) \
		FIRESTORE_PROJECT=$(GCP_PROJECT) \
		./deploy/auth_broker/deploy.sh

deploy-prescription-worker:
	GCP_PROJECT=$(GCP_PROJECT) GCP_REGION=$(GCP_REGION) \
		GCS_BUCKET=$(GCS_BUCKET) FIRESTORE_PROJECT=$(GCP_PROJECT) \
		./deploy/workers/deploy.sh

# Async prescription path only — no Agent Runtime redeploy (same Reasoning Engine).
deploy-async-backend: deploy-auth-broker deploy-prescription-worker

# Convenience: full backend deploy in the right order.
# Agent Runtime first (produces deployment_metadata.json), then auth broker
# (consumes AGENT_RUNTIME_RESOURCE from that file).
deploy-backend: deploy deploy-auth-broker

# Convenience: Flutter PWA build + Firebase Hosting deploy.
# Requires `flutterfire configure` was run once for this project.
FIREBASE_PROJECT ?= $(GCP_PROJECT)
HOSTING_URL ?= https://$(FIREBASE_PROJECT).web.app
deploy-frontend:
	cd frontend && flutter build web --release \
		--dart-define=API_BASE_URL=$(HOSTING_URL) \
		--dart-define=ENVIRONMENT=production
	firebase deploy --only hosting,firestore:rules --project $(FIREBASE_PROJECT)
