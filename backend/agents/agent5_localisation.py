"""
backend/agents/agent5_localisation.py
Agent 5: Localisation + Audio

Translates the English medication explanation to the patient's preferred language
and generates TTS audio. Runs in-process as the final step of the SequentialAgent
under Agent Runtime (Day 5 §3.3).

Day 5 context hygiene: the system instruction uses `[[PLACEHOLDER]]` tokens
resolved per-request by backend/policy/context_resolver.py against
specs/schemas/language_map.yaml — no severity tone or disclaimer ever reaches
the model as a raw literal.
"""
from __future__ import annotations

import logging
import re

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from pydantic import BaseModel

from llm_models import LOCALISATION_AUDIO_LLM, gemini
from policy.context_resolver import (
    ContextResolver,
    ContextResolverError,
    RenderContext,
)
from tools.tts import tts_tool

logger = logging.getLogger(__name__)


# ── Data contracts ────────────────────────────────────────────────────────────


class LocalisationInput(BaseModel):
    explanation_text: str
    target_language: str  # hi-IN | ta-IN | te-IN | bn-IN | en-IN
    severity: str


class LocalisationOutput(BaseModel):
    translated_text: str
    audio_url: str
    language_code: str


# ── Instruction template (placeholders resolved per-request) ──────────────────

LOCALISATION_INSTRUCTION_TEMPLATE = """
You are a medical translation and audio specialist.

Given an English medication explanation (in your context), you must:

1. Translate the explanation into [[PATIENT_LANGUAGE]] faithfully.
   - Do NOT change meaning, add commentary, or alter clinical content.
   - Match the severity-appropriate tone: [[SEVERITY_TONE]].
   - The consult-your-doctor disclaimer MUST appear in the translated text. The
     exact form for this language is:
       [[DISCLAIMER]]
   - If [[PATIENT_LANGUAGE]] is "en-IN", do not translate — use the text as-is
     and ensure the English disclaimer is present.
2. Call text_to_speech(text=<translated_text>, language_code=[[PATIENT_LANGUAGE]]).
3. Return a LocalisationOutput JSON object:
   - translated_text: the translated (or original) explanation
   - audio_url: the URL returned by text_to_speech
   - language_code: [[PATIENT_LANGUAGE]]

Output ONLY a LocalisationOutput JSON object. No preamble.
"""


_TARGET_LANGUAGE_RE = re.compile(
    r"Target language:\s*(hi-IN|ta-IN|te-IN|bn-IN|en-IN)", re.IGNORECASE
)
_DEFAULT_LANGUAGE = "en-IN"
_SUPPORTED = {"hi-IN", "ta-IN", "te-IN", "bn-IN", "en-IN"}


def _target_language_from_state(callback_context: CallbackContext) -> str:
    """Best-effort extraction of target_language from the active session.

    Priority: explicit session state key → `Target language: <code>` in any
    user message in this invocation → default en-IN.
    """
    state = callback_context.state
    candidate = state.get("target_language")
    if isinstance(candidate, str) and candidate in _SUPPORTED:
        return candidate

    invocation_ctx = callback_context.get_invocation_context()
    try:
        session = invocation_ctx.session
        for event in reversed(session.events or []):
            if not getattr(event, "content", None):
                continue
            for part in event.content.parts or []:
                text = getattr(part, "text", None) or ""
                match = _TARGET_LANGUAGE_RE.search(text)
                if match:
                    return match.group(1)
    except Exception:  # noqa: BLE001  — best-effort fallback only
        logger.debug("Could not read session events for target_language; defaulting")

    return _DEFAULT_LANGUAGE


def _overall_severity_from_state(callback_context: CallbackContext) -> str:
    """Pull overall_severity from session state (set by Agent 3/4)."""
    state = callback_context.state
    for key in ("overall_severity", "severity"):
        value = state.get(key)
        if isinstance(value, str) and value.upper() in {
            "HIGH",
            "MODERATE",
            "LOW",
            "INFO",
            "NONE",
        }:
            return value.upper()
    return "INFO"


_RESOLVER = ContextResolver()


async def resolve_localisation_instruction(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> None:
    """ADK before_model_callback — resolve `[[PLACEHOLDER]]` tokens in the
    localisation system instruction against the current session context.

    Fail-closed: if resolution raises, we replace the instruction with a
    short safe instruction that still produces a valid LocalisationOutput in
    English, so the user never receives a partially-rendered template.
    """
    language = _target_language_from_state(callback_context)
    severity = _overall_severity_from_state(callback_context)
    render_ctx = RenderContext(
        patient_language=language,
        overall_severity=severity,
    )

    try:
        resolved = _RESOLVER.resolve(LOCALISATION_INSTRUCTION_TEMPLATE, render_ctx)
    except ContextResolverError as exc:
        logger.error(
            "ContextResolver failed (session=%s lang=%s severity=%s): %s",
            callback_context.session.id,
            language,
            severity,
            exc,
        )
        resolved = (
            "You are a medical translation and audio specialist. "
            "Return the English explanation unchanged with the consult-your-doctor "
            "disclaimer appended, call text_to_speech with language_code=en-IN, "
            "and produce a valid LocalisationOutput JSON object."
        )

    llm_request.config.system_instruction = resolved
    return None


def create_localisation_agent() -> LlmAgent:
    """Create and return the Localisation agent.

    The static instruction is the unresolved template — ADK will pass it
    through before_model_callback which substitutes per-request values.
    """
    return LlmAgent(
        name="localisation_audio",
        model=gemini(LOCALISATION_AUDIO_LLM),
        instruction=LOCALISATION_INSTRUCTION_TEMPLATE,
        tools=[tts_tool],
        output_schema=LocalisationOutput,
        before_model_callback=resolve_localisation_instruction,
        description=(
            "Translates prescription explanations to Hindi, Tamil, Telugu, Bengali, "
            "or English and generates TTS audio via GCP Text-to-Speech."
        ),
    )
