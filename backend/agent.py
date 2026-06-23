"""
backend/agent.py
Central ADK Agent and App definitions for the Medication Companion pipeline.

Defines the root_agent as a SequentialAgent coordinating:
1. Prescription Reader (Gate 1 OCR + vision + image classification)
2. Medication Resolver (brand -> generic lookup, FDC split)
3. Medication Safety (cross-visit drug interaction check)
4. Patient Education (plain-language English explanation)
5. Localisation + Audio (translate to patient's Indian language + TTS)

Policy server gates (Day 5 §3.2) and pipeline grounding callbacks:
- image_intake_callback + pin_extracted_drug_names on Agent 1 (after_agent_callback)
- apply_resolver_allowlist on Agent 2 (drops drugs not read by Agent 1)
- persist_visit_to_memory on the root SequentialAgent's after_agent_callback
- output_policy_callback on the root SequentialAgent's after_agent_callback
- qa_input_policy_callback on the root SequentialAgent's before_agent_callback
  (no-op until FEATURE_QA_ENABLED=true)

The legacy backend/tools/guardrails.py module remains for back-compat tests
but is no longer wired into the pipeline.
"""
from google.adk.agents import SequentialAgent
from google.adk.apps import App

from agents.agent1_reader import create_reader_agent
from agents.agent2_resolver import create_resolver_agent
from agents.agent3_safety import create_safety_agent
from agents.agent4_education import create_education_agent
from agents.agent5_localisation import create_localisation_agent
from memory.memory_service import create_memory_service
from evaluation.pipeline_eval import schedule_pipeline_eval
from policy import (
    image_intake_callback,
    output_policy_callback,
    qa_input_policy_callback,
)
from tools.patient_memory import persist_visit_to_memory
from tools.pipeline_state import (
    apply_resolver_allowlist,
    create_preload_patient_memory_callback,
    pin_extracted_drug_names,
    sync_resolver_state_for_safety,
)

memory_service = create_memory_service()


async def reader_after_callbacks(callback_context):
    """Policy image gate, then pin Agent 1 OCR names for downstream allowlist."""
    await image_intake_callback(callback_context)
    pin_extracted_drug_names(callback_context)
    return None


reader_agent = create_reader_agent(after_agent_callback=reader_after_callbacks)
resolver_agent = create_resolver_agent(
    before_agent_callback=create_preload_patient_memory_callback(memory_service),
    after_agent_callback=apply_resolver_allowlist,
)
safety_agent = create_safety_agent(
    memory_service=memory_service,
    before_agent_callback=sync_resolver_state_for_safety,
)
education_agent = create_education_agent()
localisation_agent = create_localisation_agent()


async def root_after_callbacks(callback_context):
    """Policy gate, Memory Bank write, then fire-and-forget LLM-as-Judge."""
    await output_policy_callback(callback_context)
    await persist_visit_to_memory(callback_context, memory_service)
    await schedule_pipeline_eval(callback_context)
    return None


root_agent = SequentialAgent(
    name="medication_companion",
    sub_agents=[
        reader_agent,
        resolver_agent,
        safety_agent,
        education_agent,
        localisation_agent,
    ],
    before_agent_callback=qa_input_policy_callback,
    after_agent_callback=root_after_callbacks,
    description="Prescription pipeline: read → resolve → safety → education → localise.",
)

# Define App instance.
# MUST be named "backend" to match the directory name (required for agents-cli).
app = App(
    root_agent=root_agent,
    name="backend",
)
