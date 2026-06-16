"""
backend/tools/patient_memory.py
Memory read tool and post-education write callback.

Agent 3 uses the history tool to check new drugs against prior visits.
Agent 4 triggers save_visit via after_agent_callback after successful output.
patient_id is always taken from the verified ADK user_id — never from tool args.
"""
import logging
from collections.abc import Mapping
from typing import Any

from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext
from pydantic import BaseModel

from memory.memory_service import MemoryServiceWrapper

logger = logging.getLogger(__name__)


def _generic_names_from_state(state: Mapping[str, Any]) -> list[str]:
    """Extract lowercase generic drug names from session state."""
    resolved = state.get("resolved_drugs", [])
    names: list[str] = []
    for item in resolved:
        if isinstance(item, dict):
            generic = item.get("generic_name") or item.get("generic")
        elif isinstance(item, BaseModel):
            generic = getattr(item, "generic_name", None)
        else:
            generic = getattr(item, "generic_name", None)
        if generic:
            names.append(str(generic).lower())
    return names


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
        history = await memory_service.get_medications_for_patient(patient_id)
        logger.info(
            "Loaded %d prior visit(s) from memory for patient %s",
            len(history),
            patient_id,
        )
        return history

    return FunctionTool(get_patient_medication_history)


def create_memory_write_callback(
    memory_service: MemoryServiceWrapper,
):
    """Return an ADK after_agent_callback that persists the visit to memory."""

    async def memory_write_callback(
        callback_context: CallbackContext,
    ) -> None:
        from agents.agent4_education import EducationOutput

        output = callback_context.output
        if output is None:
            return None

        if isinstance(output, dict):
            try:
                education_output = EducationOutput.model_validate(output)
            except Exception:
                logger.warning(
                    "Education output validation failed for session %s — skipping memory write",
                    callback_context.session.id,
                )
                return None
        elif isinstance(output, EducationOutput):
            education_output = output
        else:
            logger.warning(
                "Unexpected education output type %s — skipping memory write",
                type(output).__name__,
            )
            return None

        patient_id = callback_context.user_id
        resolved_drugs = _generic_names_from_state(dict(callback_context.state))
        if not resolved_drugs:
            logger.warning(
                "No resolved_drugs in session state for patient %s — skipping memory write",
                patient_id,
            )
            return None

        await memory_service.save_visit(
            patient_id=patient_id,
            resolved_drug_names=resolved_drugs,
            severity=education_output.overall_severity,
        )
        logger.info(
            "Saved visit to memory for patient %s (%d drugs, severity=%s)",
            patient_id,
            len(resolved_drugs),
            education_output.overall_severity,
        )
        return None

    return memory_write_callback
