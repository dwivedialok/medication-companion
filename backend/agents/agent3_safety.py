"""
backend/agents/agent3_safety.py
Agent 3: Reconciliation & Safety

Responsibility: Check for drug-drug interactions between:
  (a) new drugs against each other
  (b) new drugs against patient's existing medication history (from memory)

This is the highest-value agent. It uses VertexAiMemoryBankService to retrieve
cross-visit medication history — enabling safety checks no single-visit system can do.

Demonstrates Day 3 (Context Engineering / Memory):
- Reads from VertexAiMemoryBankService (long-term, cross-visit)
- Reads session state for current-visit resolved drugs (short-term)
"""
from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field

from llm_models import MEDICATION_SAFETY_LLM, gemini
from memory.memory_service import MemoryServiceWrapper
from tools.pipeline_state import generics_from_resolved_state
from tools.safety_check import create_safety_check_tool


# ── Data contracts ────────────────────────────────────────────────────────────

class Interaction(BaseModel):
    drug_a: str
    drug_b: str
    severity: str = Field(..., description="HIGH | MODERATE | LOW | INFO | NONE")
    mechanism: str = Field(..., description="Brief plain-language mechanism")
    source: str = Field(..., description="current_visit | cross_visit")


class SafetyOutput(BaseModel):
    interactions: list[Interaction]
    overall_severity: str = Field(..., description="Highest severity across all interactions")
    safe_to_proceed: bool = Field(
        ...,
        description="True unless HIGH severity interaction found — does not mean 'no action needed'"
    )


# ── Agent factory ─────────────────────────────────────────────────────────────

SAFETY_INSTRUCTION = """
You are a medication safety checker. Your ONLY job is to identify drug-drug interactions.

Rules:
- Call check_prescription_interactions exactly ONCE.
- Copy its return value into your SafetyOutput JSON:
  - interactions: use the tool's interactions list verbatim
  - overall_severity: use the tool's overall_severity verbatim
  - safe_to_proceed: use the tool's safe_to_proceed verbatim
- Do NOT call any other tools.
- Do NOT invent drug names or interactions.
- Do NOT add pharmacological reasoning beyond what the tool returned.
- If the tool returns zero interactions, output an empty interactions list.
- Output ONLY a SafetyOutput JSON object.
"""


def create_safety_agent(
    memory_service: MemoryServiceWrapper,
    before_agent_callback=None,
) -> LlmAgent:
    """Create and return the Safety agent."""
    kwargs: dict = {
        "name": "medication_safety",
        "model": gemini(MEDICATION_SAFETY_LLM),
        "instruction": SAFETY_INSTRUCTION,
        "tools": [create_safety_check_tool(memory_service)],
        "output_schema": SafetyOutput,
        "description": (
            "Checks drug-drug interactions within the current prescription and "
            "against the patient's full medication history stored in Vertex AI memory."
        ),
    }
    if before_agent_callback is not None:
        kwargs["before_agent_callback"] = before_agent_callback
    return LlmAgent(**kwargs)
