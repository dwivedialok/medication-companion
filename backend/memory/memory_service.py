"""
backend/memory/memory_service.py
MemoryServiceWrapper and factory.

Provides cross-visit medication history per patient (long-term memory).

MEMORY_BACKEND=local   → in-process dict (no GCP credentials)
MEMORY_BACKEND=vertex  → VertexAiMemoryBankService

Memory stores ONLY: resolved generic drug names, visit timestamp, severity summary.
Never stores: image data, raw LLM output, clinical notes, or diagnostic text.
"""
import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class MemoryServiceWrapper:
    """
    Stable interface for reading/writing patient medication history.
    Wraps either an in-process dict (local) or VertexAiMemoryBankService (vertex).
    """

    def __init__(self, backend: Any | None = None) -> None:
        self._backend = backend
        self._local_store: dict[str, list[dict]] = {}

    def is_local(self) -> bool:
        return self._backend is None

    async def get_medications_for_patient(self, patient_id: str) -> list[dict]:
        """
        Retrieve prior visit records for a patient.

        Returns list of dicts: {visit_timestamp, resolved_drugs, severity_summary}.
        Returns [] if no history exists.
        """
        if self.is_local():
            return list(self._local_store.get(patient_id, []))

        try:
            results = await self._backend.search_memory(
                app_name="medication-companion",
                user_id=patient_id,
                query="medication history",
            )
            return [r.get("content", {}) for r in (results or [])]
        except Exception as exc:
            logger.error(
                "Memory retrieval failed for patient %s: %s", patient_id, exc
            )
            return []

    async def save_visit(
        self,
        patient_id: str,
        resolved_drug_names: list[str],
        severity: str,
    ) -> None:
        """
        Persist this visit's medication summary.

        Only stores: generic drug names, timestamp, severity — never images or LLM output.
        """
        visit = {
            "visit_timestamp": datetime.now(timezone.utc).isoformat(),
            "resolved_drugs": resolved_drug_names,
            "severity_summary": severity,
        }

        if self.is_local():
            self._local_store.setdefault(patient_id, []).append(visit)
            return

        try:
            await self._backend.add_memory(
                app_name="medication-companion",
                user_id=patient_id,
                content=visit,
            )
        except Exception as exc:
            logger.error("Memory write failed for patient %s: %s", patient_id, exc)


def create_memory_service() -> MemoryServiceWrapper:
    """
    Return a MemoryServiceWrapper for the current environment.
    Controlled by the MEMORY_BACKEND env var (local | vertex).
    """
    backend = os.getenv("MEMORY_BACKEND", "local")

    if backend == "vertex":
        try:
            from google.adk.memory import VertexAiMemoryBankService

            project = os.getenv("GOOGLE_CLOUD_PROJECT")
            location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
            logger.info("Using VertexAiMemoryBankService (project=%s)", project)
            vertex_backend = VertexAiMemoryBankService(
                project=project,
                location=location,
            )
            return MemoryServiceWrapper(backend=vertex_backend)
        except Exception as exc:
            logger.error(
                "Failed to init VertexAiMemoryBankService: %s — falling back to local",
                exc,
            )

    logger.info("Using in-process memory store (local mode)")
    return MemoryServiceWrapper(backend=None)
