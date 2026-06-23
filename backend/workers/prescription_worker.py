"""
backend/workers/prescription_worker.py
Cloud Run worker: Pub/Sub push subscription → prescription pipeline → job store.

Not used by `make local-auth-broker` (see PUBSUB_BACKEND=inline there).
"""
from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from auth_broker.pubsub_client import decode_pubsub_push_envelope
from auth_broker.prescription_handler import process_prescription_job

load_dotenv()

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

if ENVIRONMENT == "production":
    import google.cloud.logging

    google.cloud.logging.Client().setup_logging()
else:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

logger = logging.getLogger(__name__)

app = FastAPI(title="Medication Companion Prescription Worker", version="1.0.0")


@app.get("/health")
async def health() -> dict:
    return {
        "status": "healthy",
        "service": "medication-companion-prescription-worker",
        "environment": ENVIRONMENT,
    }


@app.post("/")
async def pubsub_push(request: Request) -> Response:
    """Receive Pub/Sub push deliveries for prescription-jobs."""
    try:
        envelope = await request.json()
        message = decode_pubsub_push_envelope(envelope)
    except (ValueError, TypeError) as exc:
        logger.warning("Invalid Pub/Sub push payload: %s", exc)
        return JSONResponse(status_code=400, content={"error": "invalid_message"})

    try:
        await process_prescription_job(message)
    except Exception as exc:
        logger.error("Job processing failed: %s", exc, exc_info=True)
        return Response(status_code=500)

    return Response(status_code=204)


logger.info("Prescription worker started (env=%s)", ENVIRONMENT)
