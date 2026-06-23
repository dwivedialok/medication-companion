"""
backend/policy/

Hybrid Policy Server for Medication Companion (Day 5 §3.2).

Two gates active in v1 (image-only):
- Image intake (structural): runs after Agent 1, deny when image_classification
  is anything other than "prescription".
- Output (semantic): runs after Agent 4 / Agent 5, denies diagnostic / dosing /
  OTC-substitution / cross-patient-leak language.

One gate deferred behind FEATURE_QA_ENABLED:
- Q&A input (regex): reuses backend/tools/guardrails.py patterns, activated when
  free-text chat is enabled in v2.

The ContextResolver (§3.3) lives alongside the gates because they share the
same "context hygiene" contract: structural inputs become resolved values
before they reach the model.
"""
from policy.context_resolver import (
    ContextResolver,
    ContextResolverError,
    RenderContext,
)
from policy.policy_server import (
    PolicyDecision,
    PolicyStage,
    ViolationClass,
    evaluate_agent_output,
    evaluate_image_intake,
    evaluate_qa_input,
    image_intake_callback,
    output_policy_callback,
    qa_input_policy_callback,
)

__all__ = [
    "ContextResolver",
    "ContextResolverError",
    "PolicyDecision",
    "PolicyStage",
    "RenderContext",
    "ViolationClass",
    "evaluate_agent_output",
    "evaluate_image_intake",
    "evaluate_qa_input",
    "image_intake_callback",
    "output_policy_callback",
    "qa_input_policy_callback",
]
