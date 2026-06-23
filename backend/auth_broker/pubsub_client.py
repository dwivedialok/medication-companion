"""
backend/auth_broker/pubsub_client.py
Publish prescription analysis jobs to Pub/Sub (or inline for local dev).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Protocol

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1


def build_job_message(
    *,
    job_id: str,
    patient_id: str,
    gcs_uri: str,
    language: str,
    content_type: str,
) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "job_id": job_id,
        "patient_id": patient_id,
        "gcs_uri": gcs_uri,
        "language": language,
        "content_type": content_type,
    }


class JobPublisher(Protocol):
    async def publish(self, message: dict) -> None: ...


class InlineJobPublisher:
    """Local/test: run worker logic in-process after enqueue."""

    async def publish(self, message: dict) -> None:
        from auth_broker.prescription_handler import process_prescription_job

        asyncio.create_task(process_prescription_job(message))
        logger.info("Inline job scheduled: %s", message.get("job_id"))


class PubSubJobPublisher:
    """Production: publish to a GCP Pub/Sub topic."""

    def __init__(self, topic_path: str) -> None:
        from google.cloud import pubsub_v1

        self._publisher = pubsub_v1.PublisherClient()
        self._topic_path = topic_path

    async def publish(self, message: dict) -> None:
        data = json.dumps(message).encode("utf-8")
        job_id = message.get("job_id", "")

        def _publish():
            future = self._publisher.publish(
                self._topic_path,
                data,
                job_id=job_id,
            )
            return future.result()

        await asyncio.to_thread(_publish)
        logger.info("Published job %s to %s", job_id, self._topic_path)


def pubsub_backend() -> str:
    explicit = os.getenv("PUBSUB_BACKEND")
    if explicit:
        return explicit
    if os.getenv("ENVIRONMENT", "development") == "local":
        return "inline"
    return "pubsub"


def _resolve_gcp_project() -> str:
    for key in (
        "GOOGLE_CLOUD_PROJECT",
        "FIRESTORE_PROJECT",
        "FIREBASE_PROJECT_ID",
        "GCP_PROJECT",
    ):
        value = os.getenv(key, "").strip()
        if value:
            return value
    raise RuntimeError(
        "GCP project id required for PUBSUB_BACKEND=pubsub "
        "(set GOOGLE_CLOUD_PROJECT, FIRESTORE_PROJECT, or FIREBASE_PROJECT_ID)"
    )


def get_job_publisher() -> JobPublisher:
    backend = pubsub_backend()
    if backend == "inline":
        return InlineJobPublisher()
    if backend == "pubsub":
        topic = os.getenv("PUBSUB_TOPIC", "prescription-jobs")
        project = _resolve_gcp_project()
        topic_path = f"projects/{project}/topics/{topic}"
        return PubSubJobPublisher(topic_path)
    raise ValueError(f"Unknown PUBSUB_BACKEND: {backend}")


def decode_pubsub_push_envelope(envelope: dict) -> dict:
    """Decode a Pub/Sub push subscription HTTP body into a job message dict."""
    import base64

    message = envelope.get("message") or {}
    raw = message.get("data")
    if not raw:
        raise ValueError("Pub/Sub message missing data")
    if isinstance(raw, str):
        payload = base64.b64decode(raw)
    else:
        payload = base64.b64decode(raw)
    data = json.loads(payload.decode("utf-8"))
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"Unsupported job schema_version: {data.get('schema_version')}")
    return data
