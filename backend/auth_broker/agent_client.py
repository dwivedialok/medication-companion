"""
backend/auth_broker/agent_client.py
Run the medication pipeline via local ADK Runner or remote Agent Runtime.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import httpx
from google.adk.events.event import Event
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agent import root_agent

logger = logging.getLogger(__name__)

APP_NAME = "medication-companion"
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _parse_gcs_uri(gcs_uri: str) -> tuple[str, str]:
    if not gcs_uri.startswith("gs://"):
        raise ValueError(f"Invalid GCS URI: {gcs_uri}")
    path = gcs_uri[len("gs://") :]
    bucket_name, _, blob_name = path.partition("/")
    if not bucket_name or not blob_name:
        raise ValueError(f"Invalid GCS URI: {gcs_uri}")
    return bucket_name, blob_name


def _download_gcs_bytes(gcs_uri: str) -> bytes:
    from google.cloud import storage

    bucket_name, blob_name = _parse_gcs_uri(gcs_uri)
    client = storage.Client()
    return client.bucket(bucket_name).blob(blob_name).download_as_bytes()


def _image_part(gcs_uri: str, mime_type: str, *, inline_bytes: bool) -> types.Part:
    """
    Build the vision Part for Agent 1.

    Local ADK Runner uses the Gemini API (not Vertex), which cannot read gs://
    URIs — download from GCS and send inline bytes instead. Remote Agent Runtime
    uses Vertex and keeps the gs:// URI.
    """
    if inline_bytes:
        return types.Part.from_bytes(
            data=_download_gcs_bytes(gcs_uri),
            mime_type=mime_type,
        )
    return types.Part.from_uri(file_uri=gcs_uri, mime_type=mime_type)


def _build_user_message(
    gcs_uri: str,
    mime_type: str,
    language: str,
    *,
    inline_image: bool = False,
) -> types.Content:
    return types.Content(
        role="user",
        parts=[
            types.Part.from_text(
                text=(
                    "Please analyse this prescription image. "
                    f"Target language: {language}"
                )
            ),
            _image_part(gcs_uri, mime_type, inline_bytes=inline_image),
        ],
    )


def _content_dict(
    gcs_uri: str,
    mime_type: str,
    language: str,
    *,
    inline_image: bool = False,
) -> dict[str, Any]:
    return _build_user_message(
        gcs_uri, mime_type, language, inline_image=inline_image
    ).model_dump(mode="json")


def _agent_runtime_resource() -> str | None:
    explicit = os.getenv("AGENT_RUNTIME_RESOURCE", "").strip()
    if explicit and explicit.lower() != "none":
        return explicit

    metadata_path = _REPO_ROOT / "deployment_metadata.json"
    if metadata_path.exists():
        try:
            data = json.loads(metadata_path.read_text(encoding="utf-8"))
            resource = data.get("remote_agent_runtime_id")
            if resource and str(resource).lower() != "none":
                return str(resource)
        except (json.JSONDecodeError, OSError) as exc:
            logger.debug("Could not read deployment_metadata.json: %s", exc)
    return None


def _stream_url(resource: str) -> tuple[str, str]:
    """Return (base_url, path) for the Agent Runtime streamQuery endpoint."""
    parts = resource.split("/")
    # projects/{p}/locations/{l}/reasoningEngines/{id}
    project_id = parts[1]
    location = parts[3]
    engine_id = parts[5]
    base_url = f"https://{location}-aiplatform.googleapis.com"
    path = (
        f"/v1/projects/{project_id}/locations/{location}/"
        f"reasoningEngines/{engine_id}:streamQuery"
    )
    return base_url, path


async def _run_local(
    *,
    patient_id: str,
    gcs_uri: str,
    mime_type: str,
    language: str,
) -> tuple[str, list[Any]]:
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=patient_id,
    )
    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )
    message = _build_user_message(
        gcs_uri, mime_type, language, inline_image=True
    )
    events: list[Any] = []
    async for event in runner.run_async(
        user_id=patient_id,
        session_id=session.id,
        new_message=message,
    ):
        events.append(event)
    return session.id, events


async def _run_remote(
    *,
    patient_id: str,
    gcs_uri: str,
    mime_type: str,
    language: str,
) -> tuple[str, list[Any]]:
    import google.auth.transport.requests

    resource = _agent_runtime_resource()
    if not resource:
        raise RuntimeError(
            "AGENT_RUNTIME_RESOURCE is not configured and deployment_metadata.json "
            "has no remote_agent_runtime_id."
        )

    base_url, path = _stream_url(resource)
    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    creds.refresh(google.auth.transport.requests.Request())
    token = creds.token

    payload = {
        "class_method": "async_stream_query",
        "input": {
            "user_id": patient_id,
            "message": _content_dict(gcs_uri, mime_type, language),
        },
    }

    events: list[Any] = []
    session_id = ""

    async with httpx.AsyncClient(timeout=180.0) as client:
        async with client.stream(
            "POST",
            f"{base_url}{path}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=payload,
            params={"alt": "sse"},
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(chunk, dict) and chunk.get("code", 200) >= 400:
                    raise RuntimeError(
                        chunk.get("message", "Agent Runtime stream error")
                    )
                if isinstance(chunk, dict) and chunk.get("session_id"):
                    session_id = str(chunk["session_id"])
                events.append(Event.model_validate(chunk))

    if not session_id:
        session_id = f"runtime-{patient_id}"
    return session_id, events


async def run_prescription_pipeline(
    *,
    patient_id: str,
    gcs_uri: str,
    mime_type: str,
    language: str,
) -> tuple[str, list[Any]]:
    """
    Execute the medication pipeline and return (session_id, events).

    Uses the remote Agent Runtime when AGENT_RUNTIME_RESOURCE or
    deployment_metadata.json is configured; otherwise falls back to a local
    in-process ADK Runner (playground / dev mode).
    """
    use_remote = os.getenv("USE_LOCAL_RUNNER", "").lower() not in ("1", "true", "yes")
    if use_remote and _agent_runtime_resource():
        logger.info("Running pipeline via Agent Runtime")
        return await _run_remote(
            patient_id=patient_id,
            gcs_uri=gcs_uri,
            mime_type=mime_type,
            language=language,
        )

    logger.info("Running pipeline via local ADK Runner")
    return await _run_local(
        patient_id=patient_id,
        gcs_uri=gcs_uri,
        mime_type=mime_type,
        language=language,
    )
