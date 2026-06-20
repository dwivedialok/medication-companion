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

from llm_models import MEDICATION_SAFETY_LLM
from memory.memory_service import MemoryServiceWrapper
from tools.interaction_lookup import interaction_lookup_tool
from tools.patient_memory import create_patient_history_tool


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
- First call get_patient_medication_history to load prior visits from memory.
- Build the full pair list: every NEW drug against every other NEW drug, and
  every NEW drug against every EXISTING drug from patient memory.
- For EACH pair, call interaction_lookup(generic_a, generic_b) FIRST.
  - If it returns severity in {HIGH, MODERATE, LOW, INFO} with source='dataset',
    trust that value verbatim. Use it as the Interaction.severity and produce a
    short plain-language mechanism (1 sentence, non-diagnostic).
  - If it returns severity='NONE' with source='none', fall back to pharmacological
    reasoning:
      * If you have strong pharmacological knowledge of an interaction, emit it
        with the appropriate severity.
      * Otherwise emit INFO severity with mechanism
        "Insufficient data to assess interaction between <drug_a> and <drug_b>."
        (substitute the actual drug names).
- Use the canonical generic name (lowercase) for drug_a and drug_b in the output.
- Source field: 'current_visit' for NEW-vs-NEW pairs, 'cross_visit' for
  NEW-vs-EXISTING pairs.
- Severity levels are STRICTLY: HIGH, MODERATE, LOW, INFO, NONE — no others.
- Do NOT generate explanations, summaries, or patient-facing text.
- NEVER invent drug names or interactions not supported by pharmacological knowledge.
- Output ONLY a SafetyOutput JSON object.
"""


def create_safety_agent(memory_service: MemoryServiceWrapper) -> LlmAgent:
    """Create and return the Safety agent."""
    return LlmAgent(
        name="medication_safety",
        model=MEDICATION_SAFETY_LLM,
        instruction=SAFETY_INSTRUCTION,
        tools=[
            create_patient_history_tool(memory_service),
            interaction_lookup_tool,
        ],
        output_schema=SafetyOutput,
        description=(
            "Checks drug-drug interactions within the current prescription and "
            "against the patient's full medication history stored in Vertex AI memory."
        ),
    )
