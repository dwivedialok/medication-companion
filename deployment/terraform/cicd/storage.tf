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
  region                = var.region
  user_project_override = true
}

resource "google_storage_bucket" "logs_data_bucket" {
  for_each                    = toset(local.all_project_ids)
  name                        = "${each.value}-${var.project_name}-logs"
  location                    = var.region
  project                     = each.value
  uniform_bucket_level_access = true
  force_destroy               = true

  depends_on = [resource.google_project_service.cicd_services, resource.google_project_service.deploy_project_services]
}

# Per-environment prescription uploads + TTS audio bucket. Read/write IAM is
# granted via project-level roles/storage.admin (app_sa + vertex_sa in iam.tf).
resource "google_storage_bucket" "uploads" {
  for_each                    = local.deploy_project_ids
  name                        = "${each.value}-${var.uploads_bucket_suffix}"
  location                    = var.region
  project                     = each.value
  uniform_bucket_level_access = true

  cors {
    origin          = ["*"]
    method          = ["GET", "PUT", "POST"]
    response_header = ["Content-Type", "Authorization"]
    max_age_seconds = 3600
  }

  depends_on = [resource.google_project_service.deploy_project_services]
}

