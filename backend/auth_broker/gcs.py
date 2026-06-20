"""
backend/auth_broker/gcs.py
GCS signed-URL helpers for prescription image upload.
"""
from __future__ import annotations

import datetime
import os
import uuid

SUPPORTED_MIME = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/heic",
}

_EXT_FOR_MIME = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/heic": "heic",
}


def gcs_bucket() -> str:
    return os.getenv("GCS_BUCKET", "medication-companion-uploads")


def validate_mime(content_type: str) -> str:
    normalized = (content_type or "image/jpeg").lower()
    if normalized not in SUPPORTED_MIME:
        raise ValueError(f"Unsupported content type: {content_type}")
    return normalized


def gcs_upload_hint(exc: Exception) -> str:
    """Actionable hint for local-dev GCS failures (safe to show to developers)."""
    msg = str(exc).lower()
    bucket = gcs_bucket()
    if "does not exist" in msg or "notfound" in msg or "404" in msg:
        return (
            f"GCS bucket gs://{bucket} does not exist in your GCP project. "
            "Create it once: ./scripts/setup_gcp.sh --project $GOOGLE_CLOUD_PROJECT"
        )
    if "private key" in msg or "sign credentials" in msg:
        return (
            "User ADC credentials cannot sign GCS URLs. "
            "In local dev use POST /upload-direct instead."
        )
    if "permission" in msg or "403" in msg:
        return (
            "GCS permission denied. Run: gcloud auth application-default login "
            f"and ensure your account can write to gs://{bucket}."
        )
    return str(exc)


def create_upload_target(content_type: str) -> dict[str, str]:
    """
    Return a V4 signed PUT URL and the destination gs:// URI.

    Raises:
        ValueError: unsupported MIME type.
        RuntimeError: GCS client or signing credentials unavailable.
    """
    from google.cloud import storage

    mime = validate_mime(content_type)
    ext = _EXT_FOR_MIME.get(mime, "jpg")
    blob_name = f"prescriptions/{uuid.uuid4().hex}.{ext}"
    bucket_name = gcs_bucket()
    gcs_uri = f"gs://{bucket_name}/{blob_name}"

    client = storage.Client()
    blob = client.bucket(bucket_name).blob(blob_name)
    upload_url = blob.generate_signed_url(
        version="v4",
        expiration=datetime.timedelta(minutes=15),
        method="PUT",
        content_type=mime,
    )

    return {
        "upload_url": upload_url,
        "gcs_uri": gcs_uri,
        "content_type": mime,
        "expires_in_seconds": "900",
    }
