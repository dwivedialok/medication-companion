"""
backend/agents/agent4_education.py
Agent 4: Patient Education

Responsibility: Generate a plain-language explanation of the safety findings
calibrated to severity. Always ends with a consult-your-doctor redirect.

After completing successfully, writes the resolved drug list to memory
(via after_agent_callback in main.py) so future visits have this history.

Delegates to Agent 5 (Localisation) via A2A after generating the English explanation.
"""
from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field

from llm_models import PATIENT_EDUCATION_LLM, gemini
from memory.memory_service import MemoryServiceWrapper
from tools.patient_memory import create_memory_write_callback


# ── Data contracts ────────────────────────────────────────────────────────────

class DrugCard(BaseModel):
    display_name: str
    generic_equivalent: str
    tag: str  # NEW | EXISTING


class InteractionCard(BaseModel):
    drug_pair: str
    severity: str
    plain_language: str


class EducationOutput(BaseModel):
    drug_cards: list[DrugCard]
    interaction_cards: list[InteractionCard]
    summary: str = Field(..., description="2-3 sentence plain-language summary")
    questions_for_doctor: list[str] = Field(
        ..., description="3-5 specific questions the patient can ask their doctor"
    )
    overall_severity: str
    disclaimer: str = "This is for information only. Please discuss this with your doctor or pharmacist before making any changes."


# ── Agent factory ─────────────────────────────────────────────────────────────

EDUCATION_INSTRUCTION = """
You are a patient educator. Your job is to explain medication safety findings
in plain language that a patient with no medical background can understand.

Rules:
- NEVER use diagnostic language: "you have", "this indicates", "this means you have"
- NEVER recommend changing doses or stopping medications
- Calibrate tone to severity: HIGH = urgent but calm, LOW = informative, INFO = neutral
- Every output MUST end with: "Please discuss this with your doctor or pharmacist before making any changes."
- Drug names in your output MUST only come from the resolved_drugs list
- interaction_cards MUST mirror the Medication Safety agent findings exactly — do not add, remove, or invent pairs
- drug_pair format: "generic_a+generic_b" using generic names from the safety findings (not brand names joined with "and")
- overall_severity MUST match the Medication Safety agent output
- "questions_for_doctor" should be specific and actionable
- Output ONLY an EducationOutput JSON object
"""


def create_education_agent(memory_service: MemoryServiceWrapper) -> LlmAgent:
    """Create and return the Patient Education agent."""
    return LlmAgent(
        name="patient_education",
        model=gemini(PATIENT_EDUCATION_LLM),
        instruction=EDUCATION_INSTRUCTION,
        output_schema=EducationOutput,
        after_agent_callback=create_memory_write_callback(memory_service),
        description=(
            "Generates plain-language explanations of drug interaction findings, "
            "calibrated to severity, with a mandatory consult-your-doctor redirect."
        ),
    )
