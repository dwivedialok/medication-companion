"""
backend/a2a_server.py
Agent 5 A2A service entry point.

Agent 5 (Localisation + Audio) is deployed as a SEPARATE Cloud Run service
communicating via the A2A protocol. This separation demonstrates Day 2:
two independently deployable agents communicating via standard protocol.

Agent 4 sends the English explanation here; Agent 5:
1. Translates to the patient's language (hi-IN, ta-IN, te-IN, bn-IN, en-IN)
2. Generates audio via GCP Text-to-Speech
3. Uploads MP3 to Cloud Storage
4. Returns signed URL

The Agent Card at /.well-known/agent.json describes Agent 5's capabilities
in the A2A standard format.
"""
import os
import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from google.adk import LlmAgent
from google.adk.a2a import to_a2a

from tools.tts import tts_tool

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
logger = logging.getLogger(__name__)


# ── Agent 5 definition ────────────────────────────────────────────────────────

LOCALISATION_INSTRUCTION = """
You are a localisation and audio specialist. Your job is to:
1. Translate the English explanation text into the target_language
2. Generate audio using the tts tool
3. Return the GCS signed URL and translated text

Rules:
- Do NOT change the meaning of the explanation text — translate only
- Do NOT remove or alter the consult-your-doctor disclaimer
- Preserve severity tone in translation
- Supported languages: hi-IN, ta-IN, te-IN, bn-IN, en-IN
"""

localisation_agent = LlmAgent(
    name="localisation_audio",
    model="gemini-2.0-flash",
    instruction=LOCALISATION_INSTRUCTION,
    tools=[tts_tool],
    description=(
        "Translates prescription explanations and generates audio in Hindi, Tamil, "
        "Telugu, Bengali, and English. Deployed as an A2A service."
    ),
)


# ── Mount as A2A-compliant FastAPI app ────────────────────────────────────────
docs_url = None if ENVIRONMENT == "production" else "/docs"
app = to_a2a(localisation_agent, docs_url=docs_url)


# ── Health endpoint ───────────────────────────────────────────────────────────
@app.get("/health")
async def health() -> dict:
    return {
        "status": "healthy",
        "service": "medication-companion-a2a",
        "environment": ENVIRONMENT,
    }


logger.info("Medication Companion A2A service started (env=%s)", ENVIRONMENT)
