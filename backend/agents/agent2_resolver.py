"""
backend/agents/agent2_resolver.py
Agent 2: Medication Resolver

Responsibility: Resolve brand names to generics, split fixed-dose combinations (FDCs).
Tags each drug as NEW (first time seen) or EXISTING (in patient memory).

Demonstrates Day 2 (Tools & Interoperability):
- FunctionTools for external API calls (RxNav) and local lookup (combo_splitter)
- The agent decides autonomously which tools to call based on the drug name
"""
from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field

from llm_models import DRUG_NAME_RESOLVER_LLM, gemini
from tools.drug_lookup import drug_lookup_tool
from tools.combo_splitter import combo_splitter_tool


# ── Data contracts ────────────────────────────────────────────────────────────

class ResolvedDrug(BaseModel):
    raw_name: str
    generic_name: str
    drug_class: str | None = None
    components: list[str] = Field(default_factory=list, description="Components if FDC")
    tag: str = Field(..., description="NEW or EXISTING or UNRESOLVED")
    confidence: float


class ResolverOutput(BaseModel):
    resolved_drugs: list[ResolvedDrug]
    unresolved_count: int


# ── Agent factory ─────────────────────────────────────────────────────────────

RESOLVER_INSTRUCTION = """
You are a medication resolver. Your ONLY job is to:
1. Resolve each drug name from brand name to generic name using the drug_lookup tool
2. Split any fixed-dose combination (FDC) products using the combo_splitter tool
3. Tag each drug as NEW (not in patient history) or EXISTING (seen before)
4. Tag as UNRESOLVED if neither tool can identify the drug

Do NOT check for interactions. Do NOT explain anything to the patient.
Output ONLY a ResolverOutput JSON object.

Lookup order for each drug:
1. Call drug_lookup(brand_name)
2. If it is an FDC, also call combo_splitter(drug_name) to get components
3. If both return no result: tag as UNRESOLVED

For EXISTING/NEW tagging: check session state for this patient's prior drug list.
"""


def create_resolver_agent() -> LlmAgent:
    """Create and return the Medication Resolver agent."""
    return LlmAgent(
        name="medication_resolver",
        model=gemini(DRUG_NAME_RESOLVER_LLM),
        instruction=RESOLVER_INSTRUCTION,
        tools=[drug_lookup_tool, combo_splitter_tool],
        output_schema=ResolverOutput,
        description=(
            "Resolves brand drug names to generics, splits FDCs, tags drugs as "
            "NEW or EXISTING using RxNav API and India brand name CSV."
        ),
    )
