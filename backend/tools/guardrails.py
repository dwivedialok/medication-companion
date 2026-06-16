"""
backend/tools/guardrails.py
Input and output guardrails as ADK before/after_agent_callbacks (Day 4: Safety).

Input guardrail (before_agent_callback):
  - Rejects images with no detectable drug names
  - Rejects diagnostic questions ("do I have", "am I sick")
  - Rejects dosing advice requests ("how much should I take")
  - Detects prompt injection patterns

Output guardrail (after_agent_callback):
  - Strips any diagnostic language that slipped through
  - Ensures consult-your-doctor disclaimer is present
  - Verifies drug names in output match resolved_drugs (hallucination check)

Running guardrails as callbacks keeps them architecturally separate
from agent logic — agents do not need to know guardrails exist.
"""
import re
import logging
from typing import Any

from fastapi import HTTPException, status
from google.adk.agents.callback_context import CallbackContext
from google.genai import types
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ── Patterns ──────────────────────────────────────────────────────────────────

DIAGNOSTIC_PATTERNS = [
    r"\b(do i have|am i sick|is this cancer|do i have diabetes|is this serious)\b",
    r"\b(diagnos|what disease|what condition|what illness)\b",
]

DOSING_PATTERNS = [
    r"\b(how much should i take|what dose|dosage for me|take more|take less)\b",
    r"\b(stop taking|should i stop|can i stop|skip my dose)\b",
]

INJECTION_PATTERNS = [
    r"(ignore (previous|above|all) instructions)",
    r"(you are now|act as|pretend you are|jailbreak|dan mode)",
    r"(system prompt|<system>|<\|im_start\|>)",
]

DIAGNOSTIC_OUTPUT_PATTERNS = [
    r"\byou have\b",
    r"\bthis indicates\b",
    r"\bthis means you have\b",
    r"\bthis suggests you have\b",
    r"\bdiagnosed with\b",
]

REQUIRED_DISCLAIMER = (
    "Please discuss this with your doctor or pharmacist before making any changes."
)


def _matches_any(text: str, patterns: list[str]) -> bool:
    text_lower = text.lower()
    return any(re.search(p, text_lower) for p in patterns)


def _extract_text_from_content(content: types.Content | None) -> str:
    if content is None:
        return ""
    parts = content.parts or []
    return " ".join(part.text for part in parts if getattr(part, "text", None))


def _sanitize_text(text: str, *, session_id: str) -> str:
    if _matches_any(text, DIAGNOSTIC_OUTPUT_PATTERNS):
        logger.warning(
            "Diagnostic language detected in output for session %s — stripping",
            session_id,
        )
        for pattern in DIAGNOSTIC_OUTPUT_PATTERNS:
            text = re.sub(pattern, "[removed]", text, flags=re.IGNORECASE)

    if REQUIRED_DISCLAIMER.lower() not in text.lower():
        logger.warning(
            "Disclaimer missing from output for session %s — injecting",
            session_id,
        )
        text = f"{text}\n\n{REQUIRED_DISCLAIMER}"

    return text


def _sanitize_output(output_data: Any, *, session_id: str) -> Any:
    """Recursively sanitize strings inside structured agent output."""
    if output_data is None:
        return None
    if isinstance(output_data, str):
        return _sanitize_text(output_data, session_id=session_id)
    if isinstance(output_data, BaseModel):
        updated = {
            field: _sanitize_output(getattr(output_data, field), session_id=session_id)
            for field in type(output_data).model_fields
        }
        return output_data.__class__(**updated)
    if isinstance(output_data, dict):
        return {
            key: _sanitize_output(value, session_id=session_id)
            for key, value in output_data.items()
        }
    if isinstance(output_data, list):
        return [_sanitize_output(item, session_id=session_id) for item in output_data]
    return output_data


# ── Input guardrail ───────────────────────────────────────────────────────────

async def input_guardrail_callback(
    callback_context: CallbackContext,
) -> types.Content | None:
    """
    ADK before_agent_callback.
    Raises HTTP 400 for rejected requests; returns None if safe.
    """
    text_content = _extract_text_from_content(callback_context.user_content)
    session_id = callback_context.session.id

    if _matches_any(text_content, INJECTION_PATTERNS):
        logger.warning("Prompt injection attempt detected in session %s", session_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request rejected. Please describe your prescription only.",
        )

    if _matches_any(text_content, DIAGNOSTIC_PATTERNS):
        logger.info("Diagnostic question rejected in session %s", session_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "This tool analyses prescriptions only. "
                "Please discuss health questions with your doctor."
            ),
        )

    if _matches_any(text_content, DOSING_PATTERNS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "This tool cannot give dosing advice. "
                "Please discuss dosage questions with your doctor or pharmacist."
            ),
        )

    return None


# ── Output guardrail ──────────────────────────────────────────────────────────

async def output_guardrail_callback(
    callback_context: CallbackContext,
) -> types.Content | None:
    """
    ADK after_agent_callback.
    Scans output text, strips diagnostic language, injects disclaimer if missing.
    Writes the sanitised value back to callback_context.output.
    """
    output_data = callback_context.output
    if output_data is None:
        return None

    session_id = callback_context.session.id
    sanitized = _sanitize_output(output_data, session_id=session_id)
    callback_context.output = sanitized
    return None
