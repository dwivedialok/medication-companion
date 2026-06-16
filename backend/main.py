"""
backend/main.py
FastAPI entry point for the Medication Companion main service (Agents 1-4).

POST /prescription  — submit prescription image, get PrescriptionResult JSON
GET  /health        — Cloud Run health check

Firebase Auth JWT is verified in HTTP middleware; bypassed in local mode via
DEV_PATIENT_ID. The patient_id derived from the token is stored on
request.state.patient_id and is propagated into the ADK session so that tools
and callbacks can retrieve it via ToolContext.user_id / CallbackContext.user_id.
"""
import logging
import os
import uuid
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()  # no-op if no .env file; env vars injected by Cloud Run in production
from fastapi import FastAPI, File, Form, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from google.adk.agents import SequentialAgent
from google.adk.runners import Runner
from google.genai import types

from agents.agent1_reader import create_reader_agent
from agents.agent2_resolver import create_resolver_agent
from agents.agent3_safety import create_safety_agent
from agents.agent4_education import EducationOutput, create_education_agent
from memory.memory_service import create_memory_service
from memory.session_service import create_session_service
from pipeline_output import find_education_output, find_gate1_reject, log_event_authors
from schemas import InteractionFinding, PrescriptionResult, ResolvedDrug
from tools.guardrails import input_guardrail_callback, output_guardrail_callback

# ── Config ────────────────────────────────────────────────────────────────────

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEV_PATIENT_ID = os.getenv("DEV_PATIENT_ID", "")
A2A_AGENT5_URL = os.getenv("A2A_AGENT5_URL", "http://localhost:8081")
GCS_BUCKET = os.getenv("GCS_BUCKET", "medication-companion-uploads")
APP_NAME = "medication-companion"

if ENVIRONMENT == "production":
    import google.cloud.logging
    google.cloud.logging.Client().setup_logging()
else:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

logger = logging.getLogger(__name__)

# ── Agent pipeline ────────────────────────────────────────────────────────────

session_service = create_session_service()
memory_service = create_memory_service()

reader_agent = create_reader_agent()
resolver_agent = create_resolver_agent()
safety_agent = create_safety_agent(memory_service=memory_service)
education_agent = create_education_agent(memory_service=memory_service)

root_agent = SequentialAgent(
    name="medication_companion",
    sub_agents=[reader_agent, resolver_agent, safety_agent, education_agent],
    before_agent_callback=input_guardrail_callback,
    after_agent_callback=output_guardrail_callback,
    description="Prescription pipeline: read → resolve → safety → education.",
)

runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service,
)

# ── FastAPI ───────────────────────────────────────────────────────────────────

docs_url = None if ENVIRONMENT == "production" else "/docs"
redoc_url = None if ENVIRONMENT == "production" else "/redoc"

app = FastAPI(
    title="Medication Companion",
    version="1.0.0",
    docs_url=docs_url,
    redoc_url=redoc_url,
)

ALLOWED_ORIGINS = (
    [f"https://{os.getenv('FIREBASE_PROJECT_ID')}.web.app"]
    if ENVIRONMENT == "production"
    else ["*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── Firebase Auth middleware ──────────────────────────────────────────────────

_PUBLIC_PATHS = {"/health", "/.well-known/agent.json"}


@app.middleware("http")
async def firebase_auth_middleware(request: Request, call_next):
    if request.url.path in _PUBLIC_PATHS:
        return await call_next(request)

    # Local bypass — no Firebase credentials needed
    if ENVIRONMENT == "local" and DEV_PATIENT_ID:
        request.state.patient_id = DEV_PATIENT_ID
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "unauthorized", "message": "Missing Authorization header."},
        )

    token = auth_header.removeprefix("Bearer ").strip()
    try:
        import firebase_admin
        from firebase_admin import auth as fb_auth

        if not firebase_admin._apps:
            firebase_admin.initialize_app()

        decoded = fb_auth.verify_id_token(token)
        request.state.patient_id = decoded["uid"]
    except Exception as exc:
        logger.warning("Firebase token verification failed: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "unauthorized", "message": "Invalid or expired token."},
        )

    return await call_next(request)


# ── Image helpers ─────────────────────────────────────────────────────────────

_SUPPORTED_MIME = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/heic"}


def _image_part(image_bytes: bytes, content_type: str) -> types.Part:
    """Return a Part for the image. In production, uploads to GCS first."""
    if ENVIRONMENT != "production":
        return types.Part.from_bytes(data=image_bytes, mime_type=content_type)

    import datetime

    from google.cloud import storage

    blob_name = f"prescriptions/{uuid.uuid4().hex}.jpg"
    storage_client = storage.Client()
    blob = storage_client.bucket(GCS_BUCKET).blob(blob_name)
    blob.upload_from_string(image_bytes, content_type=content_type)
    return types.Part.from_uri(
        file_uri=f"gs://{GCS_BUCKET}/{blob_name}",
        mime_type=content_type,
    )


# ── Pipeline output extraction ────────────────────────────────────────────────
# See pipeline_output.py — ADK puts JSON in event.content, not always event.output.

# ── Result assembly ───────────────────────────────────────────────────────────

def _assemble_result(
    session_id: str,
    edu: EducationOutput,
    localisation: dict[str, Any],
) -> PrescriptionResult:
    resolved_drugs = [
        ResolvedDrug(
            raw_name=card.display_name,
            generic_name=card.generic_equivalent,
            tag=card.tag,
        )
        for card in (edu.drug_cards or [])
    ]

    interactions = []
    for card in edu.interaction_cards or []:
        parts = card.drug_pair.split("+", 1)
        drug_a = parts[0].strip()
        drug_b = parts[1].strip() if len(parts) > 1 else ""
        interactions.append(
            InteractionFinding(
                drug_a=drug_a,
                drug_b=drug_b,
                severity=card.severity,
                mechanism=card.plain_language,
            )
        )

    return PrescriptionResult(
        session_id=session_id,
        resolved_drugs=resolved_drugs,
        interactions=interactions,
        overall_severity=edu.overall_severity or "NONE",
        explanation_en=edu.summary,
        explanation_localised=localisation.get("translated_text", edu.summary),
        audio_url=localisation.get("audio_url", ""),
        doctor_questions=edu.questions_for_doctor or [],
        disclaimer=edu.disclaimer,
    )


# ── POST /prescription ────────────────────────────────────────────────────────

@app.post("/prescription", response_model=PrescriptionResult)
async def analyze_prescription(
    request: Request,
    image: UploadFile = File(..., description="Prescription image (JPEG, PNG, WEBP)"),
    language: str = Form(
        default="en-IN",
        description="Audio language: hi-IN | ta-IN | te-IN | bn-IN | en-IN",
    ),
) -> Any:
    patient_id: str = request.state.patient_id

    content_type = image.content_type or "image/jpeg"
    if content_type not in _SUPPORTED_MIME:
        return JSONResponse(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            content={"error": "unsupported_media_type", "message": f"Unsupported type: {content_type}"},
        )

    image_bytes = await image.read()
    if not image_bytes:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "empty_image", "message": "Image file is empty."},
        )

    # New session per request — memory handles cross-visit state separately
    session = await session_service.create_session(app_name=APP_NAME, user_id=patient_id)
    session_id: str = session.id

    new_message = types.Content(
        role="user",
        parts=[
            types.Part.from_text(text="Please analyse this prescription image."),
            _image_part(image_bytes, content_type),
        ],
    )

    events: list = []
    async for event in runner.run_async(
        user_id=patient_id,
        session_id=session_id,
        new_message=new_message,
    ):
        events.append(event)

    gate1 = find_gate1_reject(events)
    if gate1:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "gate1_reject",
                "message": gate1.user_message,
                "reason": gate1.reason,
            },
        )

    edu = find_education_output(events)
    if edu is None:
        log_event_authors(events, session_id)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "pipeline_error", "message": "Analysis failed. Please try again."},
        )

    # Localisation via A2A — stub in local mode
    if ENVIRONMENT == "local":
        localisation: dict[str, Any] = {
            "translated_text": edu.summary,
            "audio_url": "https://stub.local/audio/stub.mp3",
        }
    else:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{A2A_AGENT5_URL}/a2a",
                    json={
                        "explanation_text": edu.summary,
                        "target_language": language,
                        "severity": edu.overall_severity or "NONE",
                    },
                )
                resp.raise_for_status()
                localisation = resp.json()
        except Exception as exc:
            logger.warning("A2A localisation call failed (non-fatal): %s", exc)
            localisation = {"translated_text": edu.summary, "audio_url": ""}

    return _assemble_result(session_id, edu, localisation)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health() -> dict:
    return {
        "status": "healthy",
        "service": "medication-companion",
        "environment": ENVIRONMENT,
    }


# ── Global error handler ──────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "internal_error", "message": "Internal server error. Please try again."},
    )


logger.info("Medication Companion started (env=%s)", ENVIRONMENT)
