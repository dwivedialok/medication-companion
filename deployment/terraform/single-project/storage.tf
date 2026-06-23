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

provider "google" {
  project               = var.project_id
  region                = var.region
  user_project_override = true
}

resource "google_storage_bucket" "logs_data_bucket" {
  name                        = "${var.project_id}-${var.project_name}-logs"
  location                    = var.region
  project                     = var.project_id
  uniform_bucket_level_access = true

  depends_on = [resource.google_project_service.services]
}

# Prescription image uploads (signed PUT URLs from auth_broker) +
# TTS audio output (signed GET URLs from Agent 5). Read/write IAM is granted
# via project-level roles/storage.admin in iam.tf (app_sa + reasoning_engine_sa).
resource "google_storage_bucket" "uploads" {
  name                        = var.uploads_bucket_name
  location                    = var.region
  project                     = var.project_id
  uniform_bucket_level_access = true

  cors {
    origin          = ["*"]
    method          = ["GET", "PUT", "POST"]
    response_header = ["Content-Type", "Authorization"]
    max_age_seconds = 3600
  }

  depends_on = [resource.google_project_service.services]
}

# Lets the dev who runs `make deploy` upload drugs.db to the uploads bucket
# (deploy-prep uses user ADC, not app_sa). Only created when dev_deployer_email is set.
resource "google_storage_bucket_iam_member" "dev_deployer_uploads" {
  count  = var.dev_deployer_email != "" ? 1 : 0
  bucket = google_storage_bucket.uploads.name
  role   = "roles/storage.objectAdmin"
  member = "user:${var.dev_deployer_email}"
}
