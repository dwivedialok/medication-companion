"""
backend/auth_broker/main.py
Thin Cloud Run token broker for Medication Companion.

Endpoints:
  GET  /health                                — health check (no auth)
  POST /upload-url                            — issue GCS signed PUT URL for prescription image upload
  POST /prescription                          — enqueue analysis (always async); returns 202 + job_id
  GET  /jobs/{job_id}                         — poll job status + result
  GET  /prescriptions                         — list past prescriptions for the authenticated patient
  GET  /prescriptions/{job_id}/image-url      — short-lived signed GET URL for the original image

Firebase JWT is verified in middleware; patient_id comes from the token UID,
never from the request body.
"""
from __future__ import annotations

import logging
import os
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, File, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from auth_broker.gcs import (
    assert_gcs_uri_owned_by_patient,
    create_read_url,
    create_upload_target,
    gcs_upload_hint,
    validate_mime,
)
from auth_broker.job_store import get_job_store
from auth_broker.pubsub_client import build_job_message, get_job_publisher
from auth_broker.auth import firebase_auth_middleware
from schemas import (
    JobError,
    PrescriptionHistoryItem,
    PrescriptionImageUrlResponse,
    PrescriptionJobEnqueueResponse,
    PrescriptionJobStatus,
    PrescriptionListResponse,
)

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
    gcs_uri: str = Field(
        ...,
        description="gs://bucket/prescriptions/{patient_id}/{uuid}.jpg",
    )
    language: str = Field(
        default="en-IN",
        description="Target language: hi-IN | ta-IN | te-IN | bn-IN | en-IN",
    )
    content_type: str = Field(
        default="image/jpeg",
        description="MIME type of the uploaded object (must match upload-url)",
    )


def _validate_prescription_input(
    body: PrescriptionRequest, patient_id: str
) -> tuple[str | None, JSONResponse | None]:
    if not body.gcs_uri.startswith("gs://"):
        return None, JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "invalid_gcs_uri",
                "message": "gcs_uri must start with gs://",
            },
        )
    try:
        mime_type = validate_mime(body.content_type)
    except ValueError as exc:
        return None, JSONResponse(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            content={"error": "unsupported_media_type", "message": str(exc)},
        )
    try:
        assert_gcs_uri_owned_by_patient(body.gcs_uri, patient_id)
    except ValueError as exc:
        return None, JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "invalid_gcs_uri",
                "message": str(exc),
            },
        )
    return mime_type, None


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
    patient_id: str = request.state.patient_id
    try:
        target = create_upload_target(body.content_type, patient_id)
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


@app.post("/prescription")
async def analyze_prescription(body: PrescriptionRequest, request: Request):
    patient_id: str = request.state.patient_id
    mime_type, err = _validate_prescription_input(body, patient_id)
    if err is not None:
        return err
    assert mime_type is not None

    return await _enqueue_prescription(
        patient_id=patient_id,
        gcs_uri=body.gcs_uri,
        language=body.language,
        content_type=mime_type,
    )


async def _enqueue_prescription(
    *,
    patient_id: str,
    gcs_uri: str,
    language: str,
    content_type: str,
) -> JSONResponse:
    job_id = uuid.uuid4().hex
    job_store = get_job_store()
    publisher = get_job_publisher()

    await job_store.create_job(
        job_id=job_id,
        patient_id=patient_id,
        gcs_uri=gcs_uri,
        language=language,
        content_type=content_type,
    )
    message = build_job_message(
        job_id=job_id,
        patient_id=patient_id,
        gcs_uri=gcs_uri,
        language=language,
        content_type=content_type,
    )
    try:
        await publisher.publish(message)
    except Exception as exc:
        logger.error("Failed to publish job %s: %s", job_id, exc, exc_info=True)
        await job_store.set_failed(
            job_id,
            JobError(
                code="internal_error",
                message="Could not queue analysis. Please try again.",
            ),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "enqueue_error",
                "message": "Could not queue analysis. Please try again.",
            },
        )

    logger.info("Enqueued prescription job %s for patient %s", job_id, patient_id)
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content=PrescriptionJobEnqueueResponse(job_id=job_id).model_dump(),
    )


@app.get("/jobs/{job_id}", response_model=PrescriptionJobStatus)
async def get_prescription_job(job_id: str, request: Request):
    patient_id: str = request.state.patient_id
    job = await get_job_store().get_job(job_id)
    if job is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "not_found", "message": "Job not found."},
        )
    if job.patient_id != patient_id:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"error": "forbidden", "message": "Job not found."},
        )
    return job


def _truncate_one_liner(text: str, *, limit: int = 140) -> str:
    first_line = text.splitlines()[0].strip()
    if len(first_line) <= limit:
        return first_line
    return first_line[: limit - 3] + "..."


def _summarise_job(job: PrescriptionJobStatus) -> PrescriptionHistoryItem:
    """Project a job document into the lighter history item shape."""
    overall_severity = None
    drug_count = None
    summary = None
    error_message = None
    if job.result is not None:
        overall_severity = job.result.overall_severity
        drug_count = len(job.result.resolved_drugs)
        text = (job.result.explanation_localised or job.result.explanation_en or "").strip()
        if text:
            summary = _truncate_one_liner(text)
    elif job.error is not None:
        error_message = job.error.message.strip() or None
        if error_message:
            summary = _truncate_one_liner(error_message)
    # Language is stored on the job doc but not on PrescriptionJobStatus; fall
    # back to the result's localised explanation locale when present.
    language = getattr(job, "language", None) or "en-IN"
    return PrescriptionHistoryItem(
        job_id=job.job_id,
        status=job.status,
        created_at=job.created_at,
        updated_at=job.updated_at,
        language=language,
        overall_severity=overall_severity,
        drug_count=drug_count,
        summary_one_liner=summary,
        error_code=(job.error.code if job.error is not None else None),
        error_message=error_message,
    )


@app.get("/prescriptions", response_model=PrescriptionListResponse)
async def list_prescriptions(request: Request, limit: int = 50):
    """
    Return the authenticated patient's past prescription analyses, newest first.
    """
    patient_id: str = request.state.patient_id
    capped_limit = max(1, min(limit, 100))
    jobs = await get_job_store().list_jobs(patient_id, limit=capped_limit)
    items = [_summarise_job(job) for job in jobs]
    return PrescriptionListResponse(items=items)


@app.get(
    "/prescriptions/{job_id}/image-url",
    response_model=PrescriptionImageUrlResponse,
)
async def get_prescription_image_url(job_id: str, request: Request):
    """
    Issue a short-lived signed GET URL for the original prescription image.
    Ownership is enforced via the job record (same pattern as GET /jobs/{job_id}).
    """
    patient_id: str = request.state.patient_id
    job = await get_job_store().get_job(job_id)
    if job is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "not_found", "message": "Prescription not found."},
        )
    if job.patient_id != patient_id:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"error": "forbidden", "message": "Prescription not found."},
        )

    gcs_uri = getattr(job, "gcs_uri", None)
    if not gcs_uri:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "not_found", "message": "Image not available."},
        )

    try:
        signed = create_read_url(gcs_uri, expires_minutes=10)
    except ValueError as exc:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "not_found", "message": str(exc)},
        )
    except Exception as exc:
        logger.error("Failed to sign read URL for job %s: %s", job_id, exc, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "image_url_error",
                "message": "Could not generate image URL.",
            },
        )

    return PrescriptionImageUrlResponse(**signed)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "internal_error", "message": "Internal server error."},
    )


logger.info("Auth broker started (env=%s, prescription_mode=async)", ENVIRONMENT)
