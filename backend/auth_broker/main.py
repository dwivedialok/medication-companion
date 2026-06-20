"""
backend/auth_broker/main.py
Thin Cloud Run token broker for Medication Companion.

Endpoints:
  GET  /health       — health check (no auth)
  POST /upload-url   — issue GCS signed PUT URL for prescription image upload
  POST /prescription — analyse image at gs:// URI via Agent Runtime (or local runner)

Firebase JWT is verified in middleware; patient_id comes from the token UID,
never from the request body.
"""
from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, File, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from auth_broker.agent_client import run_prescription_pipeline
from auth_broker.assembly import assemble_prescription_result
from auth_broker.auth import firebase_auth_middleware
from auth_broker.gcs import create_upload_target, gcs_upload_hint, validate_mime
from pipeline_output import (
    find_education_output,
    find_gate1_reject,
    find_localisation_output,
    log_event_authors,
)
from schemas import PrescriptionResult

load_dotenv()

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

if ENVIRONMENT == "production":
    import google.cloud.logging

    google.cloud.logging.Client().setup_logging()
else:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

logger = logging.getLogger(__name__)

docs_url = None if ENVIRONMENT == "production" else "/docs"
redoc_url = None if ENVIRONMENT == "production" else "/redoc"

app = FastAPI(
    title="Medication Companion Auth Broker",
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
app.middleware("http")(firebase_auth_middleware)


class UploadUrlRequest(BaseModel):
    content_type: str = Field(
        default="image/jpeg",
        description="MIME type: image/jpeg | image/png | image/webp | image/heic",
    )


class UploadUrlResponse(BaseModel):
    upload_url: str
    gcs_uri: str
    content_type: str
    expires_in_seconds: str


class PrescriptionRequest(BaseModel):
    gcs_uri: str = Field(..., description="gs://bucket/prescriptions/<uuid>.jpg")
    language: str = Field(
        default="en-IN",
        description="Target language: hi-IN | ta-IN | te-IN | bn-IN | en-IN",
    )
    content_type: str = Field(
        default="image/jpeg",
        description="MIME type of the uploaded object (must match upload-url)",
    )


@app.get("/health")
async def health() -> dict:
    return {
        "status": "healthy",
        "service": "medication-companion-auth-broker",
        "environment": ENVIRONMENT,
    }


@app.post("/upload-url", response_model=UploadUrlResponse)
async def upload_url(body: UploadUrlRequest, request: Request):
    """Issue a signed GCS PUT URL. Client uploads the image, then calls /prescription."""
    _ = request.state.patient_id  # noqa: F841 — ensures auth ran
    try:
        target = create_upload_target(body.content_type)
    except ValueError as exc:
        return JSONResponse(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            content={"error": "unsupported_media_type", "message": str(exc)},
        )
    except Exception as exc:
        logger.error("Failed to create upload URL: %s", exc)
        hint = gcs_upload_hint(exc)
        if ENVIRONMENT == "local" and "upload-direct" not in hint.lower():
            hint = f"{hint} Or use POST /upload-direct (server-side GCS upload)."
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "upload_url_error",
                "message": f"Could not create upload URL. {hint}",
            },
        )
    return UploadUrlResponse(**target)


if ENVIRONMENT == "local":

    @app.post("/upload-direct")
    async def upload_direct(
        request: Request,
        image: UploadFile = File(...),
    ):
        """
        Local-dev only: broker uploads image bytes to GCS (no signed URL needed).
        Use when user ADC credentials cannot sign URLs.
        """
        from google.cloud import storage

        patient_id = request.state.patient_id
        content_type = image.content_type or "image/jpeg"
        try:
            mime = validate_mime(content_type)
        except ValueError as exc:
            return JSONResponse(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                content={"error": "unsupported_media_type", "message": str(exc)},
            )

        image_bytes = await image.read()
        if not image_bytes:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "empty_image", "message": "Image file is empty."},
            )

        import uuid

        from auth_broker.gcs import _EXT_FOR_MIME, gcs_bucket

        ext = _EXT_FOR_MIME.get(mime, "jpg")
        blob_name = f"prescriptions/{patient_id}/{uuid.uuid4().hex}.{ext}"
        bucket_name = gcs_bucket()
        gcs_uri = f"gs://{bucket_name}/{blob_name}"

        try:
            client = storage.Client()
            blob = client.bucket(bucket_name).blob(blob_name)
            blob.upload_from_string(image_bytes, content_type=mime)
        except Exception as exc:
            logger.error("Direct upload failed: %s", exc)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "upload_error",
                    "message": f"Could not upload image to GCS. {gcs_upload_hint(exc)}",
                },
            )

        return {"gcs_uri": gcs_uri, "content_type": mime}


@app.post("/prescription", response_model=PrescriptionResult)
async def analyze_prescription(body: PrescriptionRequest, request: Request):
    patient_id: str = request.state.patient_id

    if not body.gcs_uri.startswith("gs://"):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "invalid_gcs_uri",
                "message": "gcs_uri must start with gs://",
            },
        )

    try:
        mime_type = validate_mime(body.content_type)
    except ValueError as exc:
        return JSONResponse(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            content={"error": "unsupported_media_type", "message": str(exc)},
        )

    try:
        session_id, events = await run_prescription_pipeline(
            patient_id=patient_id,
            gcs_uri=body.gcs_uri,
            mime_type=mime_type,
            language=body.language,
        )
    except Exception as exc:
        logger.error("Pipeline execution failed: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "pipeline_error",
                "message": "Analysis failed. Please try again.",
            },
        )

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

    education = find_education_output(events)
    if education is None:
        log_event_authors(events, session_id)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "pipeline_error",
                "message": "Analysis failed. Please try again.",
            },
        )

    localisation = find_localisation_output(events)
    return assemble_prescription_result(session_id, education, localisation)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "internal_error", "message": "Internal server error."},
    )


logger.info("Auth broker started (env=%s)", ENVIRONMENT)
