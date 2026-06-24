"""Unit tests for async prescription enqueue and job status API."""
import asyncio
import os
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

import auth_broker.job_store as job_store_module

os.environ.setdefault("ENVIRONMENT", "local")
os.environ.setdefault("DEV_PATIENT_ID", "broker-test-patient")
os.environ.setdefault("MEMORY_BACKEND", "local")
os.environ.setdefault("USE_LOCAL_RUNNER", "true")
os.environ.setdefault("JOB_STORE_BACKEND", "memory")
os.environ.setdefault("PUBSUB_BACKEND", "inline")


@pytest.fixture(autouse=True)
def _broker_env(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "local")
    monkeypatch.setenv("DEV_PATIENT_ID", "broker-test-patient")
    monkeypatch.setenv("JOB_STORE_BACKEND", "memory")
    monkeypatch.setenv("PUBSUB_BACKEND", "inline")
    job_store_module._memory_store = job_store_module.MemoryJobStore()


@pytest.fixture
def broker_app():
    from auth_broker.main import app

    return app


@pytest.fixture
def patient_gcs_uri():
    return "gs://test-bucket/prescriptions/broker-test-patient/rx.jpg"


@pytest.mark.asyncio
async def test_prescription_rejects_wrong_patient_gcs_path(broker_app):
    async with AsyncClient(
        transport=ASGITransport(app=broker_app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/prescription",
            json={
                "gcs_uri": "gs://test-bucket/prescriptions/other-patient/rx.jpg",
                "language": "en-IN",
            },
        )
    assert resp.status_code == 400
    assert resp.json()["error"] == "invalid_gcs_uri"


@pytest.mark.asyncio
async def test_prescription_async_returns_202(broker_app, patient_gcs_uri):
    with patch(
        "auth_broker.prescription_handler.run_prescription_pipeline",
        new=AsyncMock(return_value=("sess-1", [])),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=broker_app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/prescription",
                json={"gcs_uri": patient_gcs_uri, "language": "en-IN"},
            )
            await asyncio.sleep(0.05)
            assert resp.status_code == 202
            job_id = resp.json()["job_id"]
            job_resp = await client.get(f"/jobs/{job_id}")
    assert job_resp.status_code == 200
    assert job_resp.json()["job_id"] == job_id


@pytest.mark.asyncio
async def test_get_job_forbidden_for_other_patient(broker_app, patient_gcs_uri):
    store = job_store_module.MemoryJobStore()
    job_store_module._memory_store = store
    await store.create_job(
        job_id="secret-job",
        patient_id="other-patient",
        gcs_uri="gs://b/prescriptions/other-patient/x.jpg",
        language="en-IN",
        content_type="image/jpeg",
    )
    async with AsyncClient(
        transport=ASGITransport(app=broker_app), base_url="http://test"
    ) as client:
        resp = await client.get("/jobs/secret-job")
    assert resp.status_code == 403


def test_pubsub_project_from_firestore_env(monkeypatch):
    from auth_broker.pubsub_client import _resolve_gcp_project

    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("FIREBASE_PROJECT_ID", raising=False)
    monkeypatch.delenv("GCP_PROJECT", raising=False)
    monkeypatch.setenv("FIRESTORE_PROJECT", "medication-companion-dev")
    assert _resolve_gcp_project() == "medication-companion-dev"
