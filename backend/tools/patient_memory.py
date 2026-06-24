"""
backend/tools/patient_memory.py
Memory read tool and root-level visit persistence.

Memory writes run from the root SequentialAgent after_agent_callback because
sub-agent after_agent_callback hooks are not reliably invoked on Agent Runtime.
patient_id is always taken from the verified ADK user_id — never from tool args.
"""
import logging

from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext

from memory.memory_service import MemoryServiceWrapper
from pipeline_output import (
    find_education_output,
    find_gate1_reject,
    find_safety_tool_result,
)
from tools.pipeline_state import (
    EXTRACTED_RAW_NAMES_KEY,
    generics_from_resolved_state,
)

logger = logging.getLogger(__name__)


def create_patient_history_tool(
    memory_service: MemoryServiceWrapper,
) -> FunctionTool:
    """Return a FunctionTool that reads cross-visit medication history."""

    async def get_patient_medication_history(
        tool_context: ToolContext,
    ) -> list[dict]:
        """
        Retrieve prior visit medication records for the current patient.

        Returns a list of visit dicts with keys:
          visit_timestamp, resolved_drugs, severity_summary.
        Returns [] when the patient has no prior visits.
        """
        patient_id = tool_context.user_id
        state = getattr(tool_context, "state", {}) or {}
        search_terms = generics_from_resolved_state(state)
        if not search_terms:
            raw_names = state.get(EXTRACTED_RAW_NAMES_KEY, [])
            search_terms = [str(name) for name in raw_names if str(name).strip()]
        history = await memory_service.get_medications_for_patient(
            patient_id,
            search_terms=search_terms,
        )
        logger.info(
            "Loaded %d prior visit(s) from memory for patient %s",
            len(history),
            patient_id,
        )
        return history

    return FunctionTool(get_patient_medication_history)


def _resolved_generics_for_memory(callback_context: CallbackContext) -> list[str]:
    """Resolved generic names from session state, with safety-tool fallback."""
    resolved = generics_from_resolved_state(callback_context.state)
    if resolved:
        return resolved

    safety = find_safety_tool_result(callback_context.session.events or []) or {}
    current = safety.get("current_generics") or []
    return [str(name).lower() for name in current if name]


async def persist_visit_to_memory(
    callback_context: CallbackContext,
    memory_service: MemoryServiceWrapper,
) -> None:
    """
    Persist this visit to Memory Bank after a successful pipeline run.

    Intended for the root SequentialAgent after_agent_callback on Agent Runtime.
    """
    session_id = callback_context.session.id
    events = callback_context.session.events or []

    if find_gate1_reject(events):
        logger.info(
            "Skipping memory write — Gate 1 reject (session=%s)",
            session_id,
        )
        return None

    education = find_education_output(events)
    if education is None:
        logger.info(
            "Skipping memory write — no education output (session=%s)",
            session_id,
        )
        return None

    patient_id = callback_context.user_id
    resolved_drugs = _resolved_generics_for_memory(callback_context)
    if not resolved_drugs:
        logger.warning(
            "No resolved_drugs for patient %s — skipping memory write (session=%s)",
            patient_id,
            session_id,
        )
        return None

    await memory_service.save_visit(
        patient_id=patient_id,
        resolved_drug_names=resolved_drugs,
        severity=education.overall_severity,
    )
    logger.info(
        "Saved visit to memory for patient %s (%d drugs, severity=%s)",
        patient_id,
        len(resolved_drugs),
        education.overall_severity,
    )
    return None
