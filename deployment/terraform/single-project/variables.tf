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

variable "project_name" {
  type        = string
  description = "Project name used as a base for resource naming"
  default     = "medication-companion"
}

variable "project_id" {
  type        = string
  description = "Google Cloud Project ID for resource deployment."
}

variable "region" {
  type        = string
  description = "Google Cloud region for resource deployment."
  default     = "us-central1"
}

variable "telemetry_logs_filter" {
  type        = string
  description = "Log Sink filter for capturing telemetry data. Captures logs with the `traceloop.association.properties.log_type` attribute set to `tracing`."
  default     = "labels.service_name=\"medication-companion\" labels.type=\"agent_telemetry\""
}

variable "feedback_logs_filter" {
  type        = string
  description = "Log Sink filter for capturing feedback data. Captures logs where the `log_type` field is `feedback`."
  default     = "jsonPayload.log_type=\"feedback\" jsonPayload.service_name=\"medication-companion\""
}

variable "app_sa_roles" {
  description = "List of roles to assign to the application service account and Vertex AI Reasoning Engine service identity"
  type        = list(string)
  default = [
    "roles/aiplatform.user",
    "roles/logging.logWriter",
    "roles/cloudtrace.agent",
    "roles/storage.admin",
    "roles/serviceusage.serviceUsageConsumer",
    # TTS: no dedicated synthesis IAM role — enable texttospeech.googleapis.com
    # (apis.tf) and serviceusage.serviceUsageConsumer is sufficient for standard API.
  ]
}

variable "uploads_bucket_name" {
  description = "Name of the GCS bucket used for prescription image uploads and TTS audio output. Must be globally unique."
  type        = string
  default     = "medication-companion-uploads"
}

variable "dev_deployer_email" {
  description = "Optional. Email of the human developer who runs make deploy from their laptop. Granted objectAdmin on the uploads bucket so deploy-prep can upload drugs.db. Leave empty in CI/shared tfvars."
  type        = string
  default     = ""
}
