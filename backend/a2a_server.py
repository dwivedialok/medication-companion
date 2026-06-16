"""
backend/a2a_server.py
Agent 5 A2A service — plain FastAPI (ADK 2.2.0 has no to_a2a helper).

Endpoints:
  POST /a2a                     — run localisation + TTS, return translated text + audio URL
  GET  /.well-known/agent.json  — A2A Agent Card
  GET  /health                  — Cloud Run health check

The main service (main.py) POSTs to /a2a after the Agents 1-4 pipeline completes.
Agent 5 translates the English explanation and generates audio via GCP TTS.
"""
import logging
import os
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, Request, status

load_dotenv()  # no-op in production; loads .env for local development
from fastapi.responses import JSONResponse
from google.adk.agents import SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import BaseModel

from agents.agent5_localisation import LocalisationOutput, create_localisation_agent

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
APP_NAME = "medication-companion-a2a"

if ENVIRONMENT == "production":
    import google.cloud.logging
    google.cloud.logging.Client().setup_logging()
else:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

logger = logging.getLogger(__name__)

# ── Agent 5 runner (stateless — fresh InMemorySessionService per process) ─────

localisation_agent = create_localisation_agent()

# SequentialAgent wrapping a single agent works fine and gives us callback hooks
a2a_root = SequentialAgent(
    name="a2a_pipeline",
    sub_agents=[localisation_agent],
    description="A2A wrapper for localisation_audio agent.",
)

_session_service = InMemorySessionService()

a2a_runner = Runner(
    agent=a2a_root,
    app_name=APP_NAME,
    session_service=_session_service,
)

# ── FastAPI ───────────────────────────────────────────────────────────────────

docs_url = None if ENVIRONMENT == "production" else "/docs"

app = FastAPI(
    title="Medication Companion — A2A Service",
    version="1.0.0",
    docs_url=docs_url,
    redoc_url=None,
)

# ── A2A request/response schemas ──────────────────────────────────────────────

class A2ARequest(BaseModel):
    explanation_text: str
    target_language: str = "en-IN"
    severity: str = "NONE"


class A2AResponse(BaseModel):
    translated_text: str
    audio_url: str
    language_code: str = ""


# ── POST /a2a ─────────────────────────────────────────────────────────────────

@app.post("/a2a", response_model=A2AResponse)
async def localise(body: A2ARequest, request: Request):
    user_id = "a2a-system"
    session = await _session_service.create_session(app_name=APP_NAME, user_id=user_id)
    session_id = session.id

    prompt = (
        f"explanation_text: {body.explanation_text}\n"
        f"target_language: {body.target_language}\n"
        f"severity: {body.severity}\n"
        "Please localise and generate audio."
    )

    new_message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=prompt)],
    )

    localisation_output: LocalisationOutput | None = None
    async for event in a2a_runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=new_message,
    ):
        output = getattr(event, "output", None)
        if isinstance(output, LocalisationOutput):
            localisation_output = output
        elif isinstance(output, dict) and "translated_text" in output:
            try:
                localisation_output = LocalisationOutput.model_validate(output)
            except Exception:
                pass

    if localisation_output is None:
        logger.error("No LocalisationOutput from agent (session=%s)", session_id)
        # Graceful fallback: return original text with no audio
        return A2AResponse(
            translated_text=body.explanation_text,
            audio_url="",
            language_code=body.target_language,
        )

    return A2AResponse(
        translated_text=localisation_output.translated_text,
        audio_url=localisation_output.audio_url,
        language_code=localisation_output.language_code or body.target_language,
    )


# ── Agent Card ────────────────────────────────────────────────────────────────

_AGENT_CARD = {
    "schemaVersion": "1.0",
    "name": "medication-companion-localisation",
    "displayName": "Medication Companion — Localisation Agent",
    "description": (
        "Translates medication explanations to Hindi, Tamil, Telugu, Bengali, "
        "or English and generates Text-to-Speech audio."
    ),
    "version": "1.0.0",
    "capabilities": ["translation", "text-to-speech"],
    "inputModes": ["text"],
    "outputModes": ["text", "audio"],
    "endpoints": {
        "run": "/a2a",
        "health": "/health",
    },
    "supportedLanguages": ["hi-IN", "ta-IN", "te-IN", "bn-IN", "en-IN"],
}


@app.get("/.well-known/agent.json")
async def agent_card() -> dict:
    return _AGENT_CARD


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health() -> dict:
    return {
        "status": "healthy",
        "service": "medication-companion-a2a",
        "environment": ENVIRONMENT,
    }


# ── Global error handler ──────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception in A2A service", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "internal_error", "message": "Localisation failed. Please try again."},
    )


logger.info("Medication Companion A2A service started (env=%s)", ENVIRONMENT)
