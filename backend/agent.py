"""
backend/agent.py
Central ADK Agent and App definitions for the Medication Companion pipeline.

Defines the root_agent as a SequentialAgent coordinating:
1. Prescription Reader (Gate 1 OCR + vision)
2. Medication Resolver (brand -> generic lookup, FDC split)
3. Medication Safety (cross-visit drug interaction check)
4. Patient Education (plain-language English explanation)

Also registers the ADK App instance required by agents-cli.
"""
from google.adk.agents import SequentialAgent
from google.adk.apps import App

from agents.agent1_reader import create_reader_agent
from agents.agent2_resolver import create_resolver_agent
from agents.agent3_safety import create_safety_agent
from agents.agent4_education import create_education_agent
from memory.memory_service import create_memory_service
from tools.guardrails import input_guardrail_callback, output_guardrail_callback

# Initialize shared services
memory_service = create_memory_service()

# Instantiate pipeline agents
reader_agent = create_reader_agent()
resolver_agent = create_resolver_agent()
safety_agent = create_safety_agent(memory_service=memory_service)
education_agent = create_education_agent(memory_service=memory_service)

# Define root orchestrator agent
root_agent = SequentialAgent(
    name="medication_companion",
    sub_agents=[reader_agent, resolver_agent, safety_agent, education_agent],
    before_agent_callback=input_guardrail_callback,
    after_agent_callback=output_guardrail_callback,
    description="Prescription pipeline: read → resolve → safety → education.",
)

# Define App instance.
# MUST be named "backend" to match the directory name (required for agents-cli).
app = App(
    root_agent=root_agent,
    name="backend",
)
