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

output "app_service_account_email" {
  description = "Application service account email"
  value       = google_service_account.app_sa.email
}

output "logs_bucket_name" {
  description = "Logs storage bucket name"
  value       = google_storage_bucket.logs_data_bucket.name
}

output "uploads_bucket_name" {
  description = "Bucket for prescription image uploads and TTS audio output"
  value       = google_storage_bucket.uploads.name
}

output "vertex_reasoning_engine_sa" {
  description = "Email of the managed Vertex AI Reasoning Engine service identity (Agent Runtime runs as this SA)"
  value       = local.reasoning_engine_sa_email
}

output "auth_broker_service_name" {
  description = "Cloud Run service name for the auth broker (image revisions are pushed by deploy/auth_broker/deploy.sh)"
  value       = google_cloud_run_v2_service.auth_broker.name
}

output "auth_broker_service_url" {
  description = "Cloud Run URL for the auth broker. Browsers should NOT hit this directly — use the Firebase Hosting domain (rewrites)."
  value       = google_cloud_run_v2_service.auth_broker.uri
}

output "auth_broker_artifact_registry" {
  description = "Artifact Registry Docker repo for auth broker images (region-docker.pkg.dev/<project>/<repo>)"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.auth_broker.repository_id}"
}
