"""
backend/evaluation/pipeline_eval.py
Fire-and-forget LLM-as-Judge after the root SequentialAgent completes.

Never blocks the patient response — scheduling uses asyncio.create_task.
"""
from __future__ import annotations

import asyncio
import logging

from google.adk.agents.callback_context import CallbackContext

from llm_models import agent_model_registry
from pipeline_output import find_education_output, find_gate1_reject, find_safety_tool_result
from tools.pipeline_state import generics_from_resolved_state

logger = logging.getLogger(__name__)


def _collect_eval_inputs(callback_context: CallbackContext) -> dict | None:
    """Extract judge inputs from session events; None when eval should be skipped."""
    events = callback_context.session.events or []

    if find_gate1_reject(events):
        logger.info(
            "Skipping pipeline eval — Gate 1 reject (session=%s)",
            callback_context.session.id,
        )
        return None

    education = find_education_output(events)
    if education is None:
        logger.info(
            "Skipping pipeline eval — no education output (session=%s)",
            callback_context.session.id,
        )
        return None

    safety = find_safety_tool_result(events) or {}
    resolved = generics_from_resolved_state(callback_context.state)
    if not resolved:
        logger.info(
            "Skipping pipeline eval — no resolved drugs (session=%s)",
            callback_context.session.id,
        )
        return None

    return {
        "session_id": callback_context.session.id,
        "patient_id": callback_context.user_id or "unknown",
        "resolved_drugs": resolved,
        "interactions_found": safety.get("interactions") or [],
        "explanation_text": education.summary,
        "agent_versions": agent_model_registry(),
    }


async def _run_pipeline_eval(payload: dict) -> None:
    from evaluation.llm_judge import score_pipeline_output

    try:
        score = await score_pipeline_output(**payload)
        logger.info(
            "Pipeline eval complete (session=%s safety=%d clarity=%d flags=%d)",
            payload["session_id"],
            score.safety_score,
            score.clarity_score,
            len(score.flags),
        )
    except Exception as exc:
        logger.error(
            "Pipeline eval failed (session=%s): %s",
            payload.get("session_id"),
            exc,
        )


async def schedule_pipeline_eval(callback_context: CallbackContext) -> None:
    """Schedule async LLM-as-Judge; returns immediately."""
    payload = _collect_eval_inputs(callback_context)
    if payload is None:
        return None
    asyncio.create_task(_run_pipeline_eval(payload))
    logger.info(
        "Scheduled async pipeline eval (session=%s)",
        callback_context.session.id,
    )
    return None
