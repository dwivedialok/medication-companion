"""
backend/memory/session_service.py
Factory for the ADK session service.

MEMORY_BACKEND=local   → InMemorySessionService  (no GCP credentials needed)
MEMORY_BACKEND=vertex  → VertexAiSessionService  (requires AGENT_RUNTIME_ID)

The session service is passed directly to get_fast_api_app() and carries
short-term pipeline state within a single prescription analysis run:
  patient_id, resolved_drugs, gate1_result, visit_timestamp.
"""
import logging
import os

logger = logging.getLogger(__name__)


def create_session_service():
    """
    Return an ADK session service appropriate for the current environment.
    Controlled by the MEMORY_BACKEND env var (local | vertex).
    """
    backend = os.getenv("MEMORY_BACKEND", "local")

    if backend == "vertex":
        from google.adk.sessions import VertexAiSessionService

        project = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        runtime_id = os.getenv("AGENT_RUNTIME_ID")
        logger.info(
            "Using VertexAiSessionService (project=%s, runtime=%s)", project, runtime_id
        )
        return VertexAiSessionService(
            project=project,
            location=location,
            agent_engine_id=runtime_id,
        )

    from google.adk.sessions import InMemorySessionService

    logger.info("Using InMemorySessionService (local mode)")
    return InMemorySessionService()
