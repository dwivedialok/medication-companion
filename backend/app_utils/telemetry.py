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

import logging
import os

_CAPTURE_DISABLED = frozenset({"false", "0", "no", ""})
_CAPTURE_MODES = frozenset(
    {"NO_CONTENT", "EVENT_ONLY", "SPAN_ONLY", "SPAN_AND_EVENT"}
)


def resolve_capture_mode(raw: str | None) -> str | None:
    """Return a GenAI capture mode, or None when logging should stay disabled."""
    if raw is None:
        return None
    value = raw.strip()
    if not value or value.lower() in _CAPTURE_DISABLED:
        return None
    upper = value.upper()
    if upper in _CAPTURE_MODES:
        return upper
    if value.lower() == "true":
        # Legacy: any truthy value previously implied metadata-only logging.
        return "NO_CONTENT"
    logging.warning(
        "Unknown OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=%r — "
        "disabling prompt-response logging",
        raw,
    )
    return None


def setup_telemetry() -> str | None:
    """Configure OpenTelemetry and GenAI telemetry with GCS upload."""
    os.environ.setdefault("GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY", "true")

    bucket = os.environ.get("LOGS_BUCKET_NAME")
    capture_content = os.environ.get(
        "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "false"
    )
    mode = resolve_capture_mode(capture_content)
    if bucket and mode:
        os.environ["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] = mode
        logging.info("Prompt-response logging enabled - mode: %s", mode)
        os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_UPLOAD_FORMAT", "jsonl")
        os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_COMPLETION_HOOK", "upload")
        os.environ.setdefault(
            "OTEL_SEMCONV_STABILITY_OPT_IN", "gen_ai_latest_experimental"
        )
        commit_sha = os.environ.get("COMMIT_SHA", "dev")
        os.environ.setdefault(
            "OTEL_RESOURCE_ATTRIBUTES",
            f"service.namespace=medication-companion,service.version={commit_sha}",
        )
        path = os.environ.get("GENAI_TELEMETRY_PATH", "completions")
        os.environ.setdefault(
            "OTEL_INSTRUMENTATION_GENAI_UPLOAD_BASE_PATH",
            f"gs://{bucket}/{path}",
        )
    else:
        logging.info(
            "Prompt-response logging disabled "
            "(set LOGS_BUCKET_NAME and OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT "
            "to EVENT_ONLY or NO_CONTENT to enable)"
        )

    return bucket
