"""
backend/memory/session_service.py
Factory for the ADK session service.

MEMORY_BACKEND=local   → InMemorySessionService  (no GCP credentials needed)
MEMORY_BACKEND=vertex  → VertexAiSessionService  (requires agent engine id)

Used by local notebooks and dev runners. Agent Runtime manages sessions in
production deployments.
"""
import logging
import os

from memory.memory_service import _resolve_agent_engine_id

logger = logging.getLogger(__name__)


def create_session_service():
    """
    Return an ADK session service appropriate for the current environment.
    Controlled by the MEMORY_BACKEND env var (local | vertex).
    """
    backend = os.getenv("MEMORY_BACKEND", "local")

    if backend == "vertex":
        try:
            from google.adk.sessions import VertexAiSessionService

            project = os.getenv("GOOGLE_CLOUD_PROJECT")
            location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
            agent_engine_id = _resolve_agent_engine_id()
            if not agent_engine_id:
                raise ValueError(
                    "agent_engine_id is required for VertexAiSessionService "
                    "(set GOOGLE_CLOUD_AGENT_ENGINE_ID on Agent Runtime, or "
                    "AGENT_RUNTIME_ID / AGENT_RUNTIME_RESOURCE locally)."
                )
            logger.info(
                "Using VertexAiSessionService (project=%s, engine=%s)",
                project,
                agent_engine_id,
            )
            return VertexAiSessionService(
                project=project,
                location=location,
                agent_engine_id=agent_engine_id,
            )
        except Exception as exc:
            logger.error(
                "Failed to init VertexAiSessionService: %s — falling back to local",
                exc,
            )

    from google.adk.sessions import InMemorySessionService

    logger.info("Using InMemorySessionService (local mode)")
    return InMemorySessionService()
