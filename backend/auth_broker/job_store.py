"""
backend/auth_broker/job_store.py
Durable prescription job state (Firestore in prod, in-memory for tests/local).
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Protocol

from schemas import JobError, PrescriptionJobStatus, PrescriptionResult

logger = logging.getLogger(__name__)

JOBS_COLLECTION = "jobs"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobStore(Protocol):
    async def create_job(
        self,
        *,
        job_id: str,
        patient_id: str,
        gcs_uri: str,
        language: str,
        content_type: str,
    ) -> PrescriptionJobStatus: ...

    async def get_job(self, job_id: str) -> PrescriptionJobStatus | None: ...

    async def update_status(self, job_id: str, status: str) -> None: ...

    async def set_result(self, job_id: str, result: PrescriptionResult) -> None: ...

    async def set_failed(self, job_id: str, error: JobError) -> None: ...

    async def list_jobs(
        self, patient_id: str, limit: int = 50
    ) -> list[PrescriptionJobStatus]: ...


class MemoryJobStore:
    """In-process job store for unit tests and local dev without Firestore."""

    def __init__(self) -> None:
        self._jobs: dict[str, dict] = {}

    async def create_job(
        self,
        *,
        job_id: str,
        patient_id: str,
        gcs_uri: str,
        language: str,
        content_type: str,
    ) -> PrescriptionJobStatus:
        now = _utc_now_iso()
        doc = {
            "job_id": job_id,
            "patient_id": patient_id,
            "gcs_uri": gcs_uri,
            "language": language,
            "content_type": content_type,
            "status": "pending",
            "created_at": now,
            "updated_at": now,
            "result": None,
            "error": None,
        }
        self._jobs[job_id] = doc
        return PrescriptionJobStatus(**doc)

    async def get_job(self, job_id: str) -> PrescriptionJobStatus | None:
        doc = self._jobs.get(job_id)
        if doc is None:
            return None
        return PrescriptionJobStatus(**doc)

    async def update_status(self, job_id: str, status: str) -> None:
        doc = self._jobs.get(job_id)
        if doc is None:
            return
        doc["status"] = status
        doc["updated_at"] = _utc_now_iso()

    async def set_result(self, job_id: str, result: PrescriptionResult) -> None:
        doc = self._jobs.get(job_id)
        if doc is None:
            return
        doc["status"] = "done"
        doc["result"] = result.model_dump()
        doc["error"] = None
        doc["updated_at"] = _utc_now_iso()

    async def set_failed(self, job_id: str, error: JobError) -> None:
        doc = self._jobs.get(job_id)
        if doc is None:
            return
        doc["status"] = "failed"
        doc["error"] = error.model_dump()
        doc["result"] = None
        doc["updated_at"] = _utc_now_iso()

    async def list_jobs(
        self, patient_id: str, limit: int = 50
    ) -> list[PrescriptionJobStatus]:
        docs = [d for d in self._jobs.values() if d.get("patient_id") == patient_id]
        docs.sort(key=lambda d: d.get("created_at", ""), reverse=True)
        return [PrescriptionJobStatus(**d) for d in docs[:limit]]


class FirestoreJobStore:
    """Firestore-backed job store for deployed environments."""

    def __init__(self, project_id: str | None = None) -> None:
        from google.cloud import firestore

        self._client = firestore.Client(project=project_id)

    def _doc_ref(self, job_id: str):
        return self._client.collection(JOBS_COLLECTION).document(job_id)

    async def create_job(
        self,
        *,
        job_id: str,
        patient_id: str,
        gcs_uri: str,
        language: str,
        content_type: str,
    ) -> PrescriptionJobStatus:
        now = _utc_now_iso()
        doc = {
            "job_id": job_id,
            "patient_id": patient_id,
            "gcs_uri": gcs_uri,
            "language": language,
            "content_type": content_type,
            "status": "pending",
            "created_at": now,
            "updated_at": now,
        }

        def _write() -> None:
            self._doc_ref(job_id).set(doc)

        await asyncio.to_thread(_write)
        return PrescriptionJobStatus(**doc)

    async def get_job(self, job_id: str) -> PrescriptionJobStatus | None:
        def _read():
            snap = self._doc_ref(job_id).get()
            return snap.to_dict() if snap.exists else None

        doc = await asyncio.to_thread(_read)
        if doc is None:
            return None
        return PrescriptionJobStatus(**doc)

    async def update_status(self, job_id: str, status: str) -> None:
        def _update() -> None:
            self._doc_ref(job_id).update(
                {"status": status, "updated_at": _utc_now_iso()}
            )

        await asyncio.to_thread(_update)

    async def set_result(self, job_id: str, result: PrescriptionResult) -> None:
        def _update() -> None:
            self._doc_ref(job_id).update(
                {
                    "status": "done",
                    "result": result.model_dump(),
                    "error": None,
                    "updated_at": _utc_now_iso(),
                }
            )

        await asyncio.to_thread(_update)

    async def set_failed(self, job_id: str, error: JobError) -> None:
        def _update() -> None:
            self._doc_ref(job_id).update(
                {
                    "status": "failed",
                    "error": error.model_dump(),
                    "result": None,
                    "updated_at": _utc_now_iso(),
                }
            )

        await asyncio.to_thread(_update)

    async def list_jobs(
        self, patient_id: str, limit: int = 50
    ) -> list[PrescriptionJobStatus]:
        from google.cloud import firestore

        def _query() -> list[dict]:
            query = (
                self._client.collection(JOBS_COLLECTION)
                .where("patient_id", "==", patient_id)
                .order_by("created_at", direction=firestore.Query.DESCENDING)
                .limit(limit)
            )
            return [snap.to_dict() for snap in query.stream()]

        docs = await asyncio.to_thread(_query)
        return [PrescriptionJobStatus(**d) for d in docs if d is not None]


_memory_store: MemoryJobStore | None = None


def job_store_backend() -> str:
    explicit = os.getenv("JOB_STORE_BACKEND")
    if explicit:
        return explicit
    if os.getenv("ENVIRONMENT", "development") == "local":
        return "memory"
    return "firestore"


def get_job_store() -> JobStore:
    backend = job_store_backend()
    if backend == "memory":
        global _memory_store
        if _memory_store is None:
            _memory_store = MemoryJobStore()
        return _memory_store
    if backend == "firestore":
        project = os.getenv("FIRESTORE_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT")
        return FirestoreJobStore(project_id=project)
    raise ValueError(f"Unknown JOB_STORE_BACKEND: {backend}")
