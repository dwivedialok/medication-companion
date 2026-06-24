"""
backend/auth_broker/prescription_handler.py
Shared sync/async prescription pipeline orchestration for broker and worker.
"""
from __future__ import annotations

import logging

from auth_broker.agent_client import run_prescription_pipeline
from auth_broker.assembly import assemble_prescription_result
from auth_broker.job_store import JobStore, get_job_store
from pipeline_output import (
    find_education_output,
    find_gate1_reject,
    find_localisation_output,
    find_resolver_output,
    find_safety_output,
    find_safety_tool_result,
    log_event_authors,
)
from schemas import JobError, PrescriptionResult

logger = logging.getLogger(__name__)


async def run_sync_prescription(
    *,
    patient_id: str,
    gcs_uri: str,
    mime_type: str,
    language: str,
) -> tuple[PrescriptionResult | None, JobError | None]:
    """
    Run the full pipeline synchronously.

    Returns (result, None) on success, (None, job_error) on gate1/failure.
    """
    try:
        session_id, events = await run_prescription_pipeline(
            patient_id=patient_id,
            gcs_uri=gcs_uri,
            mime_type=mime_type,
            language=language,
        )
    except Exception as exc:
        logger.error("Pipeline execution failed: %s", exc, exc_info=True)
        return None, JobError(
            code="pipeline_error",
            message="Analysis failed. Please try again.",
        )

    gate1 = find_gate1_reject(events)
    if gate1:
        return None, JobError(
            code="gate1_reject",
            message=gate1.user_message,
            reason=gate1.reason,
        )

    education = find_education_output(events)
    if education is None:
        log_event_authors(events, session_id)
        return None, JobError(
            code="pipeline_error",
            message="Analysis failed. Please try again.",
        )

    localisation = find_localisation_output(events)
    safety_tool = find_safety_tool_result(events)
    safety_output = find_safety_output(events)
    resolver = find_resolver_output(events)
    result = assemble_prescription_result(
        session_id,
        education,
        localisation,
        resolver=resolver,
        safety_tool=safety_tool,
        safety_output=safety_output,
    )
    return result, None


async def process_prescription_job(
    message: dict,
    *,
    job_store: JobStore | None = None,
) -> None:
    """
    Worker entry: process one queued prescription job (idempotent).

    message keys: job_id, patient_id, gcs_uri, language, content_type
    """
    store = job_store or get_job_store()
    job_id = message["job_id"]
    patient_id = message["patient_id"]
    gcs_uri = message["gcs_uri"]
    language = message["language"]
    content_type = message["content_type"]

    existing = await store.get_job(job_id)
    if existing is not None and existing.status in ("processing", "done", "failed"):
        logger.info(
            "Skipping job %s — already terminal or in progress (status=%s)",
            job_id,
            existing.status,
        )
        return

    await store.update_status(job_id, "processing")
    logger.info("Processing prescription job %s for patient %s", job_id, patient_id)

    result, error = await run_sync_prescription(
        patient_id=patient_id,
        gcs_uri=gcs_uri,
        mime_type=content_type,
        language=language,
    )
    if error is not None:
        await store.set_failed(job_id, error)
        logger.info("Job %s failed: %s", job_id, error.code)
        return

    assert result is not None
    await store.set_result(job_id, result)
    logger.info("Job %s completed (session=%s)", job_id, result.session_id)
