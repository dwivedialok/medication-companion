"""
Unit tests for auth_broker HTTP endpoints (no live GCP / Agent Runtime).
"""
import os
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("ENVIRONMENT", "local")
os.environ.setdefault("DEV_PATIENT_ID", "broker-test-patient")
os.environ.setdefault("MEMORY_BACKEND", "local")
os.environ.setdefault("USE_LOCAL_RUNNER", "true")
os.environ.setdefault("JOB_STORE_BACKEND", "memory")


@pytest.fixture(autouse=True)
def _broker_env(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "local")
    monkeypatch.setenv("DEV_PATIENT_ID", "broker-test-patient")
    monkeypatch.setenv("JOB_STORE_BACKEND", "memory")
    monkeypatch.setenv("PUBSUB_BACKEND", "inline")


@pytest.fixture
def broker_app():
    from auth_broker.main import app

    return app


@pytest.mark.asyncio
async def test_health_no_auth(broker_app):
    async with AsyncClient(
        transport=ASGITransport(app=broker_app), base_url="http://test"
    ) as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["service"] == "medication-companion-auth-broker"


@pytest.mark.asyncio
async def test_upload_url_requires_no_bearer_in_local(broker_app):
    with patch(
        "auth_broker.main.create_upload_target",
        return_value={
            "upload_url": "https://storage.googleapis.com/signed",
            "gcs_uri": "gs://test-bucket/prescriptions/broker-test-patient/abc.jpg",
            "content_type": "image/jpeg",
            "expires_in_seconds": "900",
        },
    ):
        async with AsyncClient(
            transport=ASGITransport(app=broker_app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/upload-url",
                json={"content_type": "image/jpeg"},
            )
    assert resp.status_code == 200
    body = resp.json()
    assert body["gcs_uri"].startswith("gs://")
    assert "upload_url" in body


@pytest.mark.asyncio
async def test_upload_url_rejects_bad_mime(broker_app):
    async with AsyncClient(
        transport=ASGITransport(app=broker_app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/upload-url",
            json={"content_type": "application/pdf"},
        )
    assert resp.status_code == 415


@pytest.mark.asyncio
async def test_prescription_rejects_non_gs_uri(broker_app):
    async with AsyncClient(
        transport=ASGITransport(app=broker_app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/prescription",
            json={"gcs_uri": "https://example.com/x.jpg", "language": "en-IN"},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_prescription_enqueues_async(broker_app):
    """All /prescription requests now return 202 + job_id; gate1 surfaces via job status."""
    with patch(
        "auth_broker.prescription_handler.run_prescription_pipeline",
        new=AsyncMock(return_value=("sess-1", [])),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=broker_app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/prescription",
                json={
                    "gcs_uri": "gs://bucket/prescriptions/broker-test-patient/x.jpg",
                    "language": "en-IN",
                },
            )
    assert resp.status_code == 202
    assert "job_id" in resp.json()
