# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# ── Auth broker (Cloud Run) ───────────────────────────────────────────────────
#
# Thin HTTP service that verifies Firebase JWTs, issues GCS signed PUT URLs,
# and proxies prescription requests to Agent Runtime. Flutter clients reach it
# via Firebase Hosting rewrites (same-origin), so Cloud Run IAM allows public
# invoke (--allow-unauthenticated). Firebase JWT is enforced in application code.
#
# Terraform owns: service skeleton, IAM, Artifact Registry, signBlob binding.
# `make deploy-auth-broker` updates the image + AGENT_RUNTIME_RESOURCE env var
# on each push (see lifecycle.ignore_changes below to prevent TF drift).

locals {
  artifact_registry_repo_id = "${var.project_name}-broker"
  auth_broker_service_name  = "${var.project_name}-broker"
  # Placeholder image used at TF apply time. Real revisions are pushed by
  # `make deploy-auth-broker` and ignored via lifecycle below.
  auth_broker_placeholder_image = "us-docker.pkg.dev/cloudrun/container/hello"
}

# Artifact Registry repo for the auth broker Docker image.
resource "google_artifact_registry_repository" "auth_broker" {
  project       = var.project_id
  location      = var.region
  repository_id = local.artifact_registry_repo_id
  format        = "DOCKER"
  description   = "Auth broker (Firebase JWT → GCS → Agent Runtime) container images"

  depends_on = [resource.google_project_service.services]
}

# Cloud Run service. Image + env updated out-of-band by deploy script; TF only
# guarantees existence and IAM.
resource "google_cloud_run_v2_service" "auth_broker" {
  project  = var.project_id
  location = var.region
  name     = local.auth_broker_service_name

  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account = google_service_account.app_sa.email

    scaling {
      max_instance_count = 10
    }

    containers {
      image = local.auth_broker_placeholder_image

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      # Static env vars only. AGENT_RUNTIME_RESOURCE is injected by the deploy
      # script after each `agents-cli deploy` (its value changes per deploy).
      env {
        name  = "ENVIRONMENT"
        value = "production"
      }

      env {
        name  = "GCS_BUCKET"
        value = google_storage_bucket.uploads.name
      }

      env {
        name  = "FIREBASE_PROJECT_ID"
        value = var.project_id
      }
    }
  }

  lifecycle {
    # Image + env vars are managed by `make deploy-auth-broker` (gcloud run
    # deploy). Without this, every TF apply would revert the live revision to
    # the placeholder.
    ignore_changes = [
      client,
      client_version,
      template[0].containers[0].image,
      template[0].containers[0].env,
      template[0].revision,
    ]
  }

  depends_on = [
    google_artifact_registry_repository.auth_broker,
    google_project_iam_member.app_sa_roles,
  ]
}

# Firebase Hosting → broker: public Cloud Run invoke is set by deploy-auth-broker
# (--allow-unauthenticated). Hosting rewrites do not send IAM identity tokens.

# app_sa signBlob self-binding. Required for V4 GCS signed PUT URLs in
# backend/auth_broker/gcs.py (Flutter uploads prescription images via these).
# This was previously granted ad-hoc by `make grant-tts-iam`; consolidated here
# because app_sa exists at TF apply time (unlike the lazy -re SA).
resource "google_service_account_iam_member" "app_sa_signblob" {
  service_account_id = google_service_account.app_sa.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:${google_service_account.app_sa.email}"
}
