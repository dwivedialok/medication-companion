.PHONY: test auth-broker deploy deploy-dry-run deploy-status deploy-prep playground infra infra-apply post-deploy grant-tts-iam

test:
	uv run pytest

# HTTP token broker (Firebase JWT → GCS → Agent Runtime). Not Pub/Sub — that is a
# separate ambient-agent path for a later phase.
auth-broker:
	cd backend && uv run uvicorn auth_broker.main:app --reload --host 0.0.0.0 --port 8080

playground:
	agents-cli playground

GCP_PROJECT ?= medication-companion-dev
GCP_REGION ?= us-central1
GCS_BUCKET ?= medication-companion-uploads
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
DEPLOY_ENV_VARS ?= DRUGS_DB_GCS_URI=$(DRUGS_DB_GCS_URI)

# Agent Runtime inline upload is capped at 8 MB. backend/venv (~380 MB) must not
# exist. drugs.db (~54 MB) is uploaded to GCS; india_brands.csv is copied into
# backend/data/ so it ships inside the backend/ tarball.
deploy-prep:
	@if [ -d backend/venv ]; then \
		echo "ERROR: backend/venv exceeds Agent Runtime's 8 MB deploy limit."; \
		echo "  rm -rf backend/venv   # use repo-root .venv via: uv sync"; \
		exit 1; \
	fi
	mkdir -p backend/data
	cp data/india_brands.csv backend/data/
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
# (TTS) V4 GCS signed URLs. We use app_sa (not -re) because Owner cannot bind
# IAM on the Google-managed Reasoning Engine service agent.
grant-tts-iam:
	@echo "Granting roles/iam.serviceAccountTokenCreator self-binding to $(APP_SA)"; \
	echo "(Required for Agent 5 TTS V4 GCS signed URLs via IAM signBlob)"; \
	gcloud iam service-accounts add-iam-policy-binding "$(APP_SA)" \
		--project=$(GCP_PROJECT) \
		--member="serviceAccount:$(APP_SA)" \
		--role=roles/iam.serviceAccountTokenCreator --quiet
