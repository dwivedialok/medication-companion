"""
backend/policy/policy_server.py
Hybrid Policy Server (Day 5 §3.2).

evaluate_image_intake : structural gate after Agent 1 — allow only when
  image_classification == "prescription".
evaluate_agent_output : semantic gate after Agent 4 / Agent 5 — denies
  diagnostic, dosing, OTC-substitution, severity-downgrade, and
  cross-patient-leak text. Regex-backed by default; the same interface
  accepts an LLM judge via POLICY_SEMANTIC_GATE=llm (left as a hook —
  the regex detectors are deterministic and easier to test for capstone).
evaluate_qa_input     : input gate for free-text chat (deferred behind
  FEATURE_QA_ENABLED). Same rubric, regex-backed.

The ADK callback wrappers (image_intake_callback, output_policy_callback)
wire these pure functions onto SequentialAgent without leaking ADK types
into the evaluators — so they remain trivially unit-testable.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

import yaml
from google.adk.agents.callback_context import CallbackContext
from google.genai import types
from pydantic import BaseModel

from app_utils.span_attributes import annotate_policy_callback
from llm_models import PRESCRIPTION_IMAGE_READER_LLM

logger = logging.getLogger(__name__)


# ── Enums + dataclasses ───────────────────────────────────────────────────────


class PolicyStage(str, Enum):
    IMAGE_INTAKE = "image_intake"
    AGENT_OUTPUT = "agent_output"
    QA_INPUT = "qa_input"


class ViolationClass(str, Enum):
    NON_PRESCRIPTION_IMAGE = "non_prescription_image"
    OVERLAY_INJECTION = "overlay_injection"
    UNREADABLE_IMAGE = "unreadable_image"
    DIAGNOSTIC_CLAIM = "diagnostic_claim"
    DOSING_CHANGE = "dosing_change"
    OTC_ALTERNATIVE = "otc_alternative"
    SEVERITY_DOWNGRADE = "severity_downgrade"
    CROSS_PATIENT_LEAK = "cross_patient_leak"
    QA_DIAGNOSTIC_QUESTION = "qa_diagnostic_question"
    QA_DOSING_REQUEST = "qa_dosing_request"
    QA_PROMPT_INJECTION = "qa_prompt_injection"


@dataclass
class PolicyDecision:
    """Result of a policy evaluation. Allow-by-default is intentional —
    deny paths must name a violation_class so the writeup can trace it.
    """

    decision: str  # "allow" | "deny"
    stage: PolicyStage
    violation_class: ViolationClass | None = None
    reason: str = ""
    evidence: str = ""
    safe_fallback: str = ""

    @property
    def allowed(self) -> bool:
        return self.decision == "allow"


@dataclass
class OutputEvalContext:
    """Optional context for the output gate; today only forbidden_names is used,
    but the shape leaves room for the LLM-judge path (resolved_drugs, severity)."""

    resolved_drugs: list[str] = field(default_factory=list)
    forbidden_names: list[str] = field(default_factory=list)
    overall_severity: str | None = None


# ── Rubric load ───────────────────────────────────────────────────────────────

_RUBRIC_PATH = Path(__file__).parent / "rubric.yaml"


def _load_rubric() -> dict[str, Any]:
    with _RUBRIC_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


_RUBRIC = _load_rubric()
SAFE_FALLBACK: str = _RUBRIC["safe_fallback"].strip()


def _compiled_detectors(violation_key: str) -> list[re.Pattern[str]]:
    spec = _RUBRIC["violation_classes"].get(violation_key, {})
    return [re.compile(p) for p in spec.get("detectors", [])]


_OUTPUT_DETECTORS: dict[ViolationClass, list[re.Pattern[str]]] = {
    ViolationClass.DIAGNOSTIC_CLAIM: _compiled_detectors("diagnostic_claim"),
    ViolationClass.DOSING_CHANGE: _compiled_detectors("dosing_change"),
    ViolationClass.OTC_ALTERNATIVE: _compiled_detectors("otc_alternative"),
    ViolationClass.SEVERITY_DOWNGRADE: _compiled_detectors("severity_downgrade"),
}

_QA_DETECTORS: dict[ViolationClass, list[re.Pattern[str]]] = {
    ViolationClass.QA_PROMPT_INJECTION: _compiled_detectors("qa_prompt_injection"),
    ViolationClass.QA_DIAGNOSTIC_QUESTION: _compiled_detectors("qa_diagnostic_question"),
    ViolationClass.QA_DOSING_REQUEST: _compiled_detectors("qa_dosing_request"),
}


def _user_message(violation_key: str) -> str:
    spec = _RUBRIC["violation_classes"].get(violation_key, {})
    return spec.get("user_message", SAFE_FALLBACK).strip()


# ── Gate 1 of 3: image intake (structural) ────────────────────────────────────


_INTAKE_MAP = {
    "non_prescription": (
        ViolationClass.NON_PRESCRIPTION_IMAGE,
        "non_prescription_image",
    ),
    "suspected_overlay_injection": (
        ViolationClass.OVERLAY_INJECTION,
        "overlay_injection",
    ),
    "unreadable": (ViolationClass.UNREADABLE_IMAGE, "unreadable_image"),
}


def evaluate_image_intake(reader_output: Any) -> PolicyDecision:
    """Structural gate on Agent 1's ReaderOutput.

    Accepts a Pydantic ReaderOutput, a dict, or anything with an
    `image_classification` attribute. Always returns a PolicyDecision.
    """
    classification = _coerce_classification(reader_output)

    if classification == "prescription":
        return PolicyDecision(
            decision="allow",
            stage=PolicyStage.IMAGE_INTAKE,
        )

    violation, rubric_key = _INTAKE_MAP.get(
        classification,
        (ViolationClass.UNREADABLE_IMAGE, "unreadable_image"),
    )
    return PolicyDecision(
        decision="deny",
        stage=PolicyStage.IMAGE_INTAKE,
        violation_class=violation,
        reason=f"image_classification={classification}",
        safe_fallback=_user_message(rubric_key),
    )


def _coerce_classification(reader_output: Any) -> str:
    """Return the image_classification value from any reasonable container."""
    if reader_output is None:
        return "unreadable"
    if isinstance(reader_output, dict):
        value = reader_output.get("image_classification", "prescription")
    else:
        value = getattr(reader_output, "image_classification", "prescription")
    if isinstance(value, Enum):
        value = value.value
    return str(value)


# ── Gate 2 of 3: agent output (semantic) ──────────────────────────────────────


def evaluate_agent_output(
    text: str,
    context: OutputEvalContext | None = None,
) -> PolicyDecision:
    """Semantic gate on Agent 4 / Agent 5 free text.

    Regex-backed default. Returns the first matching violation_class (rubric
    is ordered diagnostic → dosing → OTC → severity_downgrade → leak).
    """
    if not text:
        return PolicyDecision(decision="allow", stage=PolicyStage.AGENT_OUTPUT)

    for violation, patterns in _OUTPUT_DETECTORS.items():
        result = _first_match(text, patterns)
        if result is not None:
            pattern, match = result
            return PolicyDecision(
                decision="deny",
                stage=PolicyStage.AGENT_OUTPUT,
                violation_class=violation,
                reason=f"detector matched: {pattern.pattern}",
                evidence=match.group(0),
                safe_fallback=SAFE_FALLBACK,
            )

    if context and context.forbidden_names:
        for name in context.forbidden_names:
            if name and name.lower() in text.lower():
                return PolicyDecision(
                    decision="deny",
                    stage=PolicyStage.AGENT_OUTPUT,
                    violation_class=ViolationClass.CROSS_PATIENT_LEAK,
                    reason="forbidden name appeared in output",
                    evidence=name,
                    safe_fallback=SAFE_FALLBACK,
                )

    return PolicyDecision(decision="allow", stage=PolicyStage.AGENT_OUTPUT)


def _first_match(
    text: str, patterns: Iterable[re.Pattern[str]]
) -> tuple[re.Pattern[str], re.Match[str]] | None:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return pattern, match
    return None


# ── Gate 3 of 3: Q&A input (deferred) ─────────────────────────────────────────

FEATURE_QA_ENABLED = os.getenv("FEATURE_QA_ENABLED", "false").lower() == "true"


def evaluate_qa_input(text: str) -> PolicyDecision:
    """Regex gate for free-text chat input. Only active when FEATURE_QA_ENABLED."""
    if not FEATURE_QA_ENABLED or not text:
        return PolicyDecision(decision="allow", stage=PolicyStage.QA_INPUT)

    for violation, patterns in _QA_DETECTORS.items():
        result = _first_match(text, patterns)
        if result is not None:
            pattern, match = result
            return PolicyDecision(
                decision="deny",
                stage=PolicyStage.QA_INPUT,
                violation_class=violation,
                reason=f"detector matched: {pattern.pattern}",
                evidence=match.group(0),
                safe_fallback=SAFE_FALLBACK,
            )

    return PolicyDecision(decision="allow", stage=PolicyStage.QA_INPUT)


# ── ADK callback wrappers ─────────────────────────────────────────────────────


REQUIRED_DISCLAIMER = (
    "Please discuss this with your doctor or pharmacist before making any changes."
)


def _extract_text(content: types.Content | None) -> str:
    if content is None:
        return ""
    parts = content.parts or []
    return " ".join(part.text for part in parts if getattr(part, "text", None))


@dataclass
class _OutputPolicyTrace:
    """Tracks the strictest policy outcome while sanitizing nested output."""

    decision: str = "allow"
    violation_class: str | None = None

    def record_deny(self, decision: PolicyDecision) -> None:
        self.decision = "deny"
        if decision.violation_class is not None:
            self.violation_class = decision.violation_class.value


def _sanitize_string(
    text: str,
    *,
    session_id: str,
    trace: _OutputPolicyTrace,
) -> str:
    """Apply the semantic gate to a single string; replace on deny."""
    decision = evaluate_agent_output(text)
    if decision.allowed:
        if REQUIRED_DISCLAIMER.lower() not in text.lower():
            logger.warning(
                "Disclaimer missing from output (session=%s) — injecting", session_id
            )
            text = f"{text}\n\n{REQUIRED_DISCLAIMER}"
        return text

    trace.record_deny(decision)
    logger.warning(
        "Policy DENY (session=%s stage=%s class=%s evidence=%r)",
        session_id,
        decision.stage.value,
        decision.violation_class.value if decision.violation_class else None,
        decision.evidence,
    )
    return decision.safe_fallback or SAFE_FALLBACK


def _sanitize_recursive(
    value: Any,
    *,
    session_id: str,
    trace: _OutputPolicyTrace,
) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        return _sanitize_string(text=value, session_id=session_id, trace=trace)
    if isinstance(value, BaseModel):
        updated = {
            field_name: _sanitize_recursive(
                getattr(value, field_name), session_id=session_id, trace=trace
            )
            for field_name in type(value).model_fields
        }
        return value.__class__(**updated)
    if isinstance(value, dict):
        return {
            k: _sanitize_recursive(v, session_id=session_id, trace=trace)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [
            _sanitize_recursive(item, session_id=session_id, trace=trace)
            for item in value
        ]
    return value


async def image_intake_callback(callback_context: CallbackContext) -> None:
    """ADK after_agent_callback on the Prescription Reader.

    Evaluates ReaderOutput.image_classification. On deny, mutates the output
    into a Gate1Reject-flavoured ReaderOutput so downstream agents see a
    refused intake. We deliberately do not raise — ADK surfaces the modified
    output to the next agent / final response.
    """
    output = callback_context.output
    if output is None:
        return None

    decision = evaluate_image_intake(output)
    session_id = callback_context.session.id
    classification = _coerce_classification(output)

    annotate_policy_callback(
        agent_name="prescription_reader",
        patient_id=getattr(callback_context, "user_id", None),
        policy_decision=decision.decision,
        image_classification=classification,
        violation_class=(
            decision.violation_class.value if decision.violation_class else None
        ),
        model=PRESCRIPTION_IMAGE_READER_LLM,
    )

    if decision.allowed:
        return None

    logger.warning(
        "Policy DENY at image_intake (session=%s class=%s reason=%s)",
        session_id,
        decision.violation_class.value if decision.violation_class else None,
        decision.reason,
    )

    # Lazy import keeps the policy module agent-agnostic.
    from agents.agent1_reader import (
        Gate1Reject,
        ImageClassification,
        ReaderOutput,
    )

    callback_context.output = ReaderOutput(
        status="gate1_reject",
        image_classification=ImageClassification(
            _coerce_classification(output)
        ),
        extracted_drugs=[],
        gate1_reject=Gate1Reject(
            reason=decision.reason or "image-intake policy deny",
            user_message=decision.safe_fallback or SAFE_FALLBACK,
        ),
    )
    return None


async def output_policy_callback(callback_context: CallbackContext) -> None:
    """ADK after_agent_callback on the root SequentialAgent.

    Walks the final output, applies the semantic gate to every string, and
    injects the consult-your-doctor disclaimer when missing. Replaces the
    legacy output_guardrail_callback in backend/tools/guardrails.py.
    """
    output = callback_context.output
    if output is None:
        return None

    session_id = callback_context.session.id
    trace = _OutputPolicyTrace()
    callback_context.output = _sanitize_recursive(
        output, session_id=session_id, trace=trace
    )
    annotate_policy_callback(
        agent_name="medication_companion",
        patient_id=getattr(callback_context, "user_id", None),
        policy_decision=trace.decision,
        violation_class=trace.violation_class,
    )
    return None


async def qa_input_policy_callback(
    callback_context: CallbackContext,
) -> types.Content | None:
    """ADK before_agent_callback for chat input (deferred behind FEATURE_QA_ENABLED).

    Returning a Content short-circuits the pipeline with the safe fallback.
    """
    text = _extract_text(callback_context.user_content)
    decision = evaluate_qa_input(text)
    annotate_policy_callback(
        agent_name="medication_companion",
        patient_id=getattr(callback_context, "user_id", None),
        policy_decision=decision.decision,
        violation_class=(
            decision.violation_class.value if decision.violation_class else None
        ),
    )
    if decision.allowed:
        return None

    logger.warning(
        "Policy DENY at qa_input (session=%s class=%s)",
        callback_context.session.id,
        decision.violation_class.value if decision.violation_class else None,
    )
    return types.Content(
        role="model",
        parts=[types.Part.from_text(text=decision.safe_fallback or SAFE_FALLBACK)],
    )
