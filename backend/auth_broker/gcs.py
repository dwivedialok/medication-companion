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


def _signed_url(
    blob,
    *,
    method: str,
    expiration: datetime.timedelta,
    content_type: str | None = None,
) -> str:
    """Return a V4 signed URL using IAM signBlob (no local private key).

    Cloud Run and Agent Runtime use metadata credentials. Pass access_token and
    service_account_email so generate_signed_url calls IAM signBlob instead.
    """
    import google.auth
    from google.auth.transport import requests as auth_requests

    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    auth_request = auth_requests.Request()
    credentials.refresh(auth_request)

    kwargs: dict = {
        "version": "v4",
        "expiration": expiration,
        "method": method,
        "service_account_email": credentials.service_account_email,
        "access_token": credentials.token,
    }
    if content_type is not None:
        kwargs["content_type"] = content_type
    return blob.generate_signed_url(**kwargs)


def create_upload_target(content_type: str, patient_id: str) -> dict[str, str]:
    """
    Return a V4 signed PUT URL and the destination gs:// URI.

    Objects are stored under prescriptions/{patient_id}/ for tenant binding.

    Raises:
        ValueError: unsupported MIME type.
        RuntimeError: GCS client or signing credentials unavailable.
    """
    from google.cloud import storage

    mime = validate_mime(content_type)
    ext = _EXT_FOR_MIME.get(mime, "jpg")
    blob_name = f"prescriptions/{patient_id}/{uuid.uuid4().hex}.{ext}"
    bucket_name = gcs_bucket()
    gcs_uri = f"gs://{bucket_name}/{blob_name}"

    client = storage.Client()
    blob = client.bucket(bucket_name).blob(blob_name)
    upload_url = _signed_url(
        blob,
        method="PUT",
        expiration=datetime.timedelta(minutes=15),
        content_type=mime,
    )

    return {
        "upload_url": upload_url,
        "gcs_uri": gcs_uri,
        "content_type": mime,
        "expires_in_seconds": "900",
    }


def create_read_url(gcs_uri: str, expires_minutes: int = 10) -> dict[str, str | int]:
    """
    Return a short-lived V4 signed GET URL for an existing prescription object.

    Used by the History UI to display the original prescription image. The
    caller MUST verify ownership before invoking this (see auth_broker/main.py).

    Raises:
        ValueError: gcs_uri is malformed.
        RuntimeError: GCS client or signing credentials unavailable.
    """
    from google.cloud import storage

    if not gcs_uri.startswith("gs://"):
        raise ValueError("gcs_uri must start with gs://")
    path = gcs_uri[len("gs://") :]
    bucket_name, _, blob_name = path.partition("/")
    if not bucket_name or not blob_name:
        raise ValueError("Invalid GCS URI")

    client = storage.Client()
    blob = client.bucket(bucket_name).get_blob(blob_name)
    if blob is None:
        raise ValueError("Prescription image not found in GCS")

    read_url = _signed_url(
        blob,
        method="GET",
        expiration=datetime.timedelta(minutes=expires_minutes),
    )
    return {
        "read_url": read_url,
        "content_type": blob.content_type or "application/octet-stream",
        "expires_in_seconds": expires_minutes * 60,
    }


def assert_gcs_uri_owned_by_patient(gcs_uri: str, patient_id: str) -> None:
    """
    Reject gcs_uri unless it points at prescriptions/{patient_id}/…

    URIs outside prescriptions/ (e.g. eval/ fixtures) are not patient uploads
    and are rejected for /prescription analysis.
    """
    if not gcs_uri.startswith("gs://"):
        raise ValueError("gcs_uri must start with gs://")

    path = gcs_uri[len("gs://") :]
    _, _, blob = path.partition("/")
    if not blob:
        raise ValueError("Invalid GCS URI")

    parts = blob.split("/")
    if len(parts) < 3 or parts[0] != "prescriptions":
        raise ValueError(
            "gcs_uri must be a prescription upload under prescriptions/{patient_id}/"
        )
    if parts[1] != patient_id:
        raise ValueError("gcs_uri does not belong to the authenticated patient")
