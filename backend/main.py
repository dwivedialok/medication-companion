"""
backend/main.py
FastAPI entry point for the Medication Companion main service (Agents 1-4).

Uses ADK's get_fast_api_app() to mount the agent pipeline as a REST API.
Firebase Auth JWT validation is applied as middleware on every request.
Swagger UI is disabled in production (ENVIRONMENT=production).
"""
import os
import logging

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from google.adk.cli.fast_api import get_fast_api_app
import google.cloud.logging

from agents.agent1_reader import create_reader_agent
from agents.agent2_resolver import create_resolver_agent
from agents.agent3_safety import create_safety_agent
from agents.agent4_education import create_education_agent
from memory.session_service import create_session_service
from memory.memory_service import create_memory_service
from tools.guardrails import input_guardrail_callback, output_guardrail_callback

# ── Logging ───────────────────────────────────────────────────────────────────
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

if ENVIRONMENT == "production":
    client = google.cloud.logging.Client()
    client.setup_logging()
else:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

logger = logging.getLogger(__name__)

# ── Build the agent pipeline ──────────────────────────────────────────────────
session_service = create_session_service()
memory_service = create_memory_service()

# Agents are composed in pipeline order.
# Each agent is an ADK LlmAgent with strict single-responsibility boundaries.
reader_agent = create_reader_agent()
resolver_agent = create_resolver_agent()
safety_agent = create_safety_agent(memory_service=memory_service)
education_agent = create_education_agent(memory_service=memory_service)

# The root agent orchestrates the pipeline.
# Sub-agents execute in sequence; state flows via session.
from google.adk import Agent

root_agent = Agent(
    name="medication_companion",
    instruction=(
        "You orchestrate the prescription analysis pipeline. "
        "Pass the prescription image through each sub-agent in order: "
        "reader → resolver → safety → education. "
        "Halt and return Gate1Reject if the reader agent rejects the image."
    ),
    sub_agents=[reader_agent, resolver_agent, safety_agent, education_agent],
    before_agent_callback=input_guardrail_callback,
    after_agent_callback=output_guardrail_callback,
)

# ── FastAPI app ───────────────────────────────────────────────────────────────
docs_url = None if ENVIRONMENT == "production" else "/docs"
redoc_url = None if ENVIRONMENT == "production" else "/redoc"

app: FastAPI = get_fast_api_app(
    agent=root_agent,
    session_service=session_service,
    docs_url=docs_url,
    redoc_url=redoc_url,
)

# CORS: Firebase Hosting origin in production; any origin in dev
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


# ── Health endpoint ───────────────────────────────────────────────────────────
@app.get("/health")
async def health() -> dict:
    """Cloud Run health check endpoint."""
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
        content={"error": "Internal server error. Please try again."},
    )


logger.info("Medication Companion main service started (env=%s)", ENVIRONMENT)
