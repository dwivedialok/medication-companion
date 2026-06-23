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

# ── Auth broker (Cloud Run) — multi-env mirror ────────────────────────────────
#
# Per-environment Cloud Run service + Artifact Registry + IAM. Mirrors
# single-project/auth_broker.tf but keyed by deploy_project_ids (staging/prod).
#
# Image + AGENT_RUNTIME_RESOURCE env var are pushed by CI
# (deploy/auth_broker/deploy.sh) — Terraform owns the skeleton only.

locals {
  auth_broker_service_name  = "${var.project_name}-broker"
  artifact_registry_repo_id = "${var.project_name}-broker"

  auth_broker_placeholder_image = "us-docker.pkg.dev/cloudrun/container/hello"
}

resource "google_artifact_registry_repository" "auth_broker" {
  for_each = local.deploy_project_ids

  project       = each.value
  location      = var.region
  repository_id = local.artifact_registry_repo_id
  format        = "DOCKER"
  description   = "Auth broker (Firebase JWT → GCS → Agent Runtime) container images"

  depends_on = [resource.google_project_service.deploy_project_services]
}

resource "google_cloud_run_v2_service" "auth_broker" {
  for_each = local.deploy_project_ids

  project  = each.value
  location = var.region
  name     = local.auth_broker_service_name

  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account = google_service_account.app_sa[each.key].email

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

      env {
        name  = "ENVIRONMENT"
        value = "production"
      }

      env {
        name  = "GCS_BUCKET"
        value = google_storage_bucket.uploads[each.key].name
      }

      env {
        name  = "FIREBASE_PROJECT_ID"
        value = each.value
      }
    }
  }

  lifecycle {
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

# Firebase Hosting → broker: public Cloud Run invoke is set by deploy-auth-broker.

# CICD runner → broker invoker (so the smoke-test step in staging.yaml can hit
# the service with its own ID token before Firebase Hosting is wired).
resource "google_cloud_run_v2_service_iam_member" "cicd_invoker" {
  for_each = local.deploy_project_ids

  project  = google_cloud_run_v2_service.auth_broker[each.key].project
  location = google_cloud_run_v2_service.auth_broker[each.key].location
  name     = google_cloud_run_v2_service.auth_broker[each.key].name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.cicd_runner_sa.email}"
}

# app_sa signBlob self-binding (per environment). Required for V4 GCS signed
# PUT URLs in backend/auth_broker/gcs.py.
resource "google_service_account_iam_member" "app_sa_signblob" {
  for_each = local.deploy_project_ids

  service_account_id = google_service_account.app_sa[each.key].name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:${google_service_account.app_sa[each.key].email}"
}
