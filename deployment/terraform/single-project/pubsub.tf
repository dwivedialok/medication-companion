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

# ── Pub/Sub: async prescription analysis (Phase A) ────────────────────────────
#
# Push subscription delivers jobs to medication-companion-prescription-worker.
# Broker publishes via roles/pubsub.publisher; worker calls Agent Runtime.

locals {
  prescription_worker_service_name = "${var.project_name}-prescription-worker"
  prescription_jobs_topic          = "prescription-jobs"
  prescription_jobs_dlq_topic        = "prescription-jobs-dlq"
  prescription_worker_placeholder  = "us-docker.pkg.dev/cloudrun/container/hello"
}

resource "google_pubsub_topic" "prescription_jobs" {
  project = var.project_id
  name    = local.prescription_jobs_topic

  depends_on = [resource.google_project_service.services]
}

resource "google_pubsub_topic" "prescription_jobs_dlq" {
  project = var.project_id
  name    = local.prescription_jobs_dlq_topic

  depends_on = [resource.google_project_service.services]
}

resource "google_cloud_run_v2_service" "prescription_worker" {
  project  = var.project_id
  location = var.region
  name     = local.prescription_worker_service_name

  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account = google_service_account.app_sa.email

    timeout = "300s"

    scaling {
      max_instance_count = 10
    }

    containers {
      image = local.prescription_worker_placeholder

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
      }

      env {
        name  = "ENVIRONMENT"
        value = "production"
      }

      env {
        name  = "GCS_BUCKET"
        value = google_storage_bucket.uploads.name
      }

      env {
        name  = "FIRESTORE_PROJECT"
        value = var.project_id
      }

      env {
        name  = "PUBSUB_BACKEND"
        value = "pubsub"
      }

      env {
        name  = "JOB_STORE_BACKEND"
        value = "firestore"
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
    google_project_iam_member.app_sa_roles,
  ]
}

resource "google_pubsub_subscription" "prescription_jobs_push" {
  project = var.project_id
  name    = "prescription-jobs-worker"
  topic   = google_pubsub_topic.prescription_jobs.id

  push_config {
    push_endpoint = "${google_cloud_run_v2_service.prescription_worker.uri}/"
    oidc_token {
      service_account_email = google_service_account.app_sa.email
    }
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.prescription_jobs_dlq.id
    max_delivery_attempts = 5
  }

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  ack_deadline_seconds = 300

  depends_on = [google_cloud_run_v2_service.prescription_worker]
}

resource "google_pubsub_subscription" "prescription_jobs_dlq_monitor" {
  project = var.project_id
  name    = "prescription-jobs-dlq-monitor"
  topic   = google_pubsub_topic.prescription_jobs_dlq.id
}

# Push subscription uses oidc_token.service_account_email = app_sa. Cloud Run
# must grant run.invoker to that SA (not the Pub/Sub service agent alone).
resource "google_cloud_run_v2_service_iam_member" "app_sa_worker_invoker" {
  project  = google_cloud_run_v2_service.prescription_worker.project
  location = google_cloud_run_v2_service.prescription_worker.location
  name     = google_cloud_run_v2_service.prescription_worker.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.app_sa.email}"
}

# Pub/Sub must mint OIDC tokens as app_sa for push delivery.
resource "google_service_account_iam_member" "pubsub_push_oidc_token_creator" {
  service_account_id = google_service_account.app_sa.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_project_iam_member" "app_sa_pubsub_publisher" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.app_sa.email}"

  depends_on = [resource.google_project_service.services]
}

resource "google_project_iam_member" "app_sa_datastore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.app_sa.email}"

  depends_on = [resource.google_project_service.services]
}
