"""
backend/memory/memory_service.py
MemoryServiceWrapper and factory.

Provides cross-visit medication history per patient (long-term memory).

MEMORY_BACKEND=local   → in-process dict (no GCP credentials)
MEMORY_BACKEND=vertex  → VertexAiMemoryBankService

Memory stores ONLY: resolved generic drug names, visit timestamp, severity summary.
Never stores: image data, raw LLM output, clinical notes, or diagnostic text.
"""
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from google.adk.memory.memory_entry import MemoryEntry
from google.genai import types

logger = logging.getLogger(__name__)

# ADK App.name on Agent Runtime (must match backend/agent.py).
_MEMORY_APP_NAME = os.getenv("ADK_APP_NAME", "backend")

# Vertex Memory Bank retrieve is semantic similarity search (top-K), not a full
# listing. Use current Rx drug names as the primary query, then merge a broad
# fallback so disjoint prior visits (cross-visit safety) are not missed.
_BROAD_MEMORY_SEARCH_QUERY = (
    "patient medication visits resolved_drugs visit_timestamp severity_summary"
)


def _resolve_agent_engine_id() -> str | None:
    """Resolve Reasoning Engine id for VertexAiMemoryBankService.

    Agent Runtime injects GOOGLE_CLOUD_AGENT_ENGINE_ID automatically. Local
    broker / tests may set AGENT_RUNTIME_ID or the full AGENT_RUNTIME_RESOURCE.
    """
    for key in (
        "GOOGLE_CLOUD_AGENT_ENGINE_ID",
        "AGENT_ENGINE_ID",
        "AGENT_RUNTIME_ID",
    ):
        value = os.getenv(key, "").strip()
        if not value:
            continue
        if "/" in value:
            return value.rsplit("/", 1)[-1]
        return value

    resource = os.getenv("AGENT_RUNTIME_RESOURCE", "").strip()
    if resource:
        return resource.rsplit("/", 1)[-1]

    return None


def _visit_to_memory_entry(visit: dict[str, Any]) -> MemoryEntry:
    """Serialize a visit dict for Vertex Memory Bank storage."""
    return MemoryEntry(
        author="system",
        content=types.Content(
            role="user",
            parts=[types.Part(text=json.dumps(visit, ensure_ascii=False))],
        ),
        timestamp=visit.get("visit_timestamp"),
    )


def _memory_entry_to_visit(entry: MemoryEntry) -> dict[str, Any] | None:
    """Parse a MemoryEntry back into a visit dict; None when not our JSON shape."""
    if not entry.content or not entry.content.parts:
        return None
    text = next((part.text for part in entry.content.parts if part.text), "")
    if not text:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    if not {"visit_timestamp", "resolved_drugs", "severity_summary"} <= data.keys():
        return None
    return data


def _build_memory_search_query(search_terms: list[str]) -> str | None:
    """Join unique drug names / OCR tokens for a Vertex similarity search."""
    cleaned: list[str] = []
    seen: set[str] = set()
    for term in search_terms:
        text = str(term).strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
    if not cleaned:
        return None
    return " ".join(cleaned)


def _merge_visits(*visit_lists: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Dedupe visit records by visit_timestamp (stable order, first wins)."""
    merged: list[dict[str, Any]] = []
    seen_timestamps: set[str] = set()
    for visits in visit_lists:
        for visit in visits:
            timestamp = str(visit.get("visit_timestamp", ""))
            if not timestamp or timestamp in seen_timestamps:
                continue
            seen_timestamps.add(timestamp)
            merged.append(visit)
    return merged


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

    async def _search_vertex_visits(
        self,
        patient_id: str,
        query: str,
    ) -> list[dict[str, Any]]:
        response = await self._backend.search_memory(
            app_name=_MEMORY_APP_NAME,
            user_id=patient_id,
            query=query,
        )
        visits: list[dict[str, Any]] = []
        for entry in response.memories or []:
            visit = _memory_entry_to_visit(entry)
            if visit is not None:
                visits.append(visit)
        return visits

    async def get_medications_for_patient(
        self,
        patient_id: str,
        *,
        search_terms: list[str] | None = None,
    ) -> list[dict]:
        """
        Retrieve prior visit records for a patient.

        When ``search_terms`` is provided (Agent 1 OCR names or resolved
        generics for the current Rx), those are used as the primary Vertex
        similarity query. A broad fallback query is always merged in so prior
        visits with disjoint drug sets remain visible for cross-visit safety.

        Returns list of dicts: {visit_timestamp, resolved_drugs, severity_summary}.
        Returns [] if no history exists.
        """
        if self.is_local():
            return list(self._local_store.get(patient_id, []))

        queries: list[str] = []
        primary_query = _build_memory_search_query(search_terms or [])
        if primary_query:
            queries.append(primary_query)
        if _BROAD_MEMORY_SEARCH_QUERY not in queries:
            queries.append(_BROAD_MEMORY_SEARCH_QUERY)

        try:
            result_sets: list[list[dict[str, Any]]] = []
            for query in queries:
                result_sets.append(
                    await self._search_vertex_visits(patient_id, query)
                )
            visits = _merge_visits(*result_sets)
            logger.info(
                "Memory retrieve for patient %s: %d visit(s) from %d search(es)",
                patient_id,
                len(visits),
                len(queries),
            )
            return visits
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
                app_name=_MEMORY_APP_NAME,
                user_id=patient_id,
                memories=[_visit_to_memory_entry(visit)],
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
            agent_engine_id = _resolve_agent_engine_id()
            if not agent_engine_id:
                raise ValueError(
                    "agent_engine_id is required for VertexAiMemoryBankService "
                    "(set GOOGLE_CLOUD_AGENT_ENGINE_ID on Agent Runtime, or "
                    "AGENT_RUNTIME_ID / AGENT_RUNTIME_RESOURCE locally)."
                )
            logger.info(
                "Using VertexAiMemoryBankService (project=%s, engine=%s, app=%s)",
                project,
                agent_engine_id,
                _MEMORY_APP_NAME,
            )
            vertex_backend = VertexAiMemoryBankService(
                project=project,
                location=location,
                agent_engine_id=agent_engine_id,
            )
            return MemoryServiceWrapper(backend=vertex_backend)
        except Exception as exc:
            logger.error(
                "Failed to init VertexAiMemoryBankService: %s — falling back to local",
                exc,
            )

    logger.info("Using in-process memory store (local mode)")
    return MemoryServiceWrapper(backend=None)
