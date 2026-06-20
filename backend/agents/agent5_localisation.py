"""
backend/agents/agent5_localisation.py
Agent 5: Localisation + Audio

Translates the English medication explanation to the patient's preferred language
and generates TTS audio. Deployed as a separate A2A service (a2a_server.py).

Translation MUST preserve semantic content — no additions, removals, or clinical
changes. The consult-your-doctor disclaimer must survive translation verbatim.
"""
from google.adk.agents import LlmAgent
from pydantic import BaseModel

from llm_models import LOCALISATION_AUDIO_LLM, gemini
from tools.tts import tts_tool


# ── Data contracts ────────────────────────────────────────────────────────────

class LocalisationInput(BaseModel):
    explanation_text: str
    target_language: str  # hi-IN | ta-IN | te-IN | bn-IN | en-IN
    severity: str


class LocalisationOutput(BaseModel):
    translated_text: str
    audio_url: str
    language_code: str


# ── Agent ─────────────────────────────────────────────────────────────────────

LOCALISATION_INSTRUCTION = """
You are a medical translation and audio specialist.

Given an English medication explanation (in your context), you must:

1. Identify the target_language from the user message (look for "Target language: <code>").
   Supported codes: hi-IN (Hindi), ta-IN (Tamil), te-IN (Telugu), bn-IN (Bengali), en-IN (English).
   Default to en-IN if not specified.
2. Translate the explanation faithfully into that language.
   - Do NOT change meaning, add commentary, or alter clinical content.
   - The consult-your-doctor disclaimer MUST appear in the translated text.
   - If target_language is "en-IN", do not translate — use the text as-is.
3. Call text_to_speech(text=<translated_text>, language_code=<target_language>).
4. Return a LocalisationOutput JSON object:
   - translated_text: the translated (or original) explanation
   - audio_url: the URL returned by text_to_speech
   - language_code: the target_language value

Supported codes: hi-IN (Hindi), ta-IN (Tamil), te-IN (Telugu), bn-IN (Bengali), en-IN (English).

Output ONLY a LocalisationOutput JSON object. No preamble.
"""


def create_localisation_agent() -> LlmAgent:
    """Create and return the Localisation agent."""
    return LlmAgent(
        name="localisation_audio",
        model=gemini(LOCALISATION_AUDIO_LLM),
        instruction=LOCALISATION_INSTRUCTION,
        tools=[tts_tool],
        output_schema=LocalisationOutput,
        description=(
            "Translates prescription explanations to Hindi, Tamil, Telugu, Bengali, "
            "or English and generates TTS audio via GCP Text-to-Speech."
        ),
    )
