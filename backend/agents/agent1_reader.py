"""
backend/agents/agent1_reader.py
Agent 1: Prescription Reader

Responsibility: Extract drug names from a prescription image using Gemini Vision.
Autonomous decision: If OCR confidence for any drug name is below threshold,
reject the prescription (Gate1Reject) and halt the pipeline.

This agent demonstrates the core agentic behaviour from Day 1:
a single LLM call would accept any image; this agent evaluates confidence
and makes a branching decision autonomously.
"""
from google.adk import LlmAgent
from google.adk.tools import FunctionTool
from pydantic import BaseModel, Field


# ── Data contracts ────────────────────────────────────────────────────────────

class ExtractedDrug(BaseModel):
    raw_name: str = Field(..., description="Drug name exactly as read from the image")
    confidence: float = Field(..., ge=0.0, le=1.0, description="OCR confidence 0–1")


class Gate1Reject(BaseModel):
    reason: str
    user_message: str = (
        "The prescription image wasn't clear enough to read safely. "
        "Please retake the photo in good lighting, keeping the text flat and in focus. "
        "Please discuss your medications with your doctor or pharmacist."
    )


class ReaderOutput(BaseModel):
    status: str  # "ok" or "gate1_reject"
    extracted_drugs: list[ExtractedDrug] = []
    gate1_reject: Gate1Reject | None = None


# ── Agent factory ─────────────────────────────────────────────────────────────

CONFIDENCE_THRESHOLD = 0.75

READER_INSTRUCTION = f"""
You are a prescription image reader. Your ONLY job is to extract drug names from the
prescription image provided. You do NOT resolve brand names, check interactions, or
make any clinical judgements.

For each drug name you can read:
- Output the name exactly as written
- Assign a confidence score from 0.0 to 1.0 based on legibility

Gate 1 rule: If ANY drug name has confidence below {CONFIDENCE_THRESHOLD},
OR if you cannot identify at least one drug name in the image,
set status="gate1_reject" with a clear reason.

Output ONLY a ReaderOutput JSON object. No other text.
"""


def create_reader_agent() -> LlmAgent:
    """Create and return the Prescription Reader agent."""
    return LlmAgent(
        name="prescription_reader",
        model="gemini-2.0-flash",
        instruction=READER_INSTRUCTION,
        output_schema=ReaderOutput,
        description=(
            "Extracts drug names from prescription images with confidence scoring. "
            "Rejects unclear images before any downstream processing (Gate 1)."
        ),
    )
