"""
Unit tests for /prescriptions list + /prescriptions/{id}/image-url endpoints.
"""
import os
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

import auth_broker.job_store as job_store_module
from schemas import (
    InteractionFinding,
    JobError,
    PrescriptionResult,
    ResolvedDrug,
)

os.environ.setdefault("ENVIRONMENT", "local")
os.environ.setdefault("DEV_PATIENT_ID", "broker-test-patient")
os.environ.setdefault("MEMORY_BACKEND", "local")
os.environ.setdefault("USE_LOCAL_RUNNER", "true")
os.environ.setdefault("JOB_STORE_BACKEND", "memory")
os.environ.setdefault("PUBSUB_BACKEND", "inline")


PATIENT = "broker-test-patient"
OTHER = "other-patient"


@pytest.fixture(autouse=True)
def _broker_env(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "local")
    monkeypatch.setenv("DEV_PATIENT_ID", PATIENT)
    monkeypatch.setenv("JOB_STORE_BACKEND", "memory")
    monkeypatch.setenv("PUBSUB_BACKEND", "inline")
    job_store_module._memory_store = job_store_module.MemoryJobStore()


@pytest.fixture
def broker_app():
    from auth_broker.main import app

    return app


def _sample_result(severity: str = "MODERATE") -> PrescriptionResult:
    return PrescriptionResult(
        session_id="sess-1",
        resolved_drugs=[
            ResolvedDrug(raw_name="Crocin 500", generic_name="paracetamol", tag="NEW"),
            ResolvedDrug(raw_name="Amox 500", generic_name="amoxicillin", tag="NEW"),
        ],
        interactions=[
            InteractionFinding(
                drug_a="paracetamol",
                drug_b="amoxicillin",
                severity="LOW",
                mechanism="None notable",
            )
        ],
        overall_severity=severity,
        explanation_en="Take with food.",
        explanation_localised="Take with food.",
        audio_url="",
        doctor_questions=[],
        disclaimer="Please discuss this with your doctor or pharmacist.",
    )


async def _seed_job(
    *, job_id: str, patient_id: str, status_: str = "done", with_result: bool = True
) -> None:
    store = job_store_module.get_job_store()
    await store.create_job(
        job_id=job_id,
        patient_id=patient_id,
        gcs_uri=f"gs://test-bucket/prescriptions/{patient_id}/{job_id}.jpg",
        language="en-IN",
        content_type="image/jpeg",
    )
    if status_ == "done" and with_result:
        await store.set_result(job_id, _sample_result())
    elif status_ != "pending":
        await store.update_status(job_id, status_)


@pytest.mark.asyncio
async def test_list_prescriptions_only_returns_own_jobs(broker_app):
    await _seed_job(job_id="mine-1", patient_id=PATIENT)
    await _seed_job(job_id="mine-2", patient_id=PATIENT, status_="processing")
    await _seed_job(job_id="theirs", patient_id=OTHER)

    async with AsyncClient(
        transport=ASGITransport(app=broker_app), base_url="http://test"
    ) as client:
        resp = await client.get("/prescriptions")

    assert resp.status_code == 200
    items = resp.json()["items"]
    job_ids = {item["job_id"] for item in items}
    assert job_ids == {"mine-1", "mine-2"}


@pytest.mark.asyncio
async def test_list_prescriptions_orders_newest_first(broker_app):
    await _seed_job(job_id="old", patient_id=PATIENT)
    await _seed_job(job_id="new", patient_id=PATIENT)
    # Force created_at ordering — the MemoryJobStore stamps on create, so
    # second insert is newer.

    async with AsyncClient(
        transport=ASGITransport(app=broker_app), base_url="http://test"
    ) as client:
        resp = await client.get("/prescriptions")

    items = resp.json()["items"]
    assert [item["job_id"] for item in items][:2] == ["new", "old"]


@pytest.mark.asyncio
async def test_list_prescriptions_projects_summary_fields(broker_app):
    await _seed_job(job_id="done-1", patient_id=PATIENT, status_="done")
    await _seed_job(job_id="pending-1", patient_id=PATIENT, status_="pending")

    async with AsyncClient(
        transport=ASGITransport(app=broker_app), base_url="http://test"
    ) as client:
        resp = await client.get("/prescriptions")

    by_id = {i["job_id"]: i for i in resp.json()["items"]}
    done_item = by_id["done-1"]
    assert done_item["overall_severity"] == "MODERATE"
    assert done_item["drug_count"] == 2
    assert done_item["summary_one_liner"]

    pending_item = by_id["pending-1"]
    assert pending_item["status"] == "pending"
    assert pending_item["overall_severity"] is None
    assert pending_item["drug_count"] is None


@pytest.mark.asyncio
async def test_list_prescriptions_projects_gate1_reject_message(broker_app):
    store = job_store_module.get_job_store()
    await store.create_job(
        job_id="gate1-1",
        patient_id=PATIENT,
        gcs_uri=f"gs://test-bucket/prescriptions/{PATIENT}/gate1-1.jpg",
        language="en-IN",
        content_type="image/jpeg",
    )
    await store.set_failed(
        "gate1-1",
        JobError(
            code="gate1_reject",
            message=(
                "That doesn't look like a prescription. Please upload a clear photo "
                "of your prescription. Please discuss this with your doctor or pharmacist."
            ),
            reason="non_prescription_image",
        ),
    )

    async with AsyncClient(
        transport=ASGITransport(app=broker_app), base_url="http://test"
    ) as client:
        resp = await client.get("/prescriptions")

    item = next(i for i in resp.json()["items"] if i["job_id"] == "gate1-1")
    assert item["status"] == "failed"
    assert item["error_code"] == "gate1_reject"
    assert "doesn't look like a prescription" in item["error_message"]
    assert "doesn't look like a prescription" in item["summary_one_liner"]


@pytest.mark.asyncio
async def test_image_url_denies_foreign_job(broker_app):
    await _seed_job(job_id="theirs", patient_id=OTHER)

    async with AsyncClient(
        transport=ASGITransport(app=broker_app), base_url="http://test"
    ) as client:
        resp = await client.get("/prescriptions/theirs/image-url")

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_image_url_returns_404_when_missing(broker_app):
    async with AsyncClient(
        transport=ASGITransport(app=broker_app), base_url="http://test"
    ) as client:
        resp = await client.get("/prescriptions/missing/image-url")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_image_url_returns_signed_url_for_owned_job(broker_app):
    await _seed_job(job_id="mine-1", patient_id=PATIENT)

    fake_signed = {
        "read_url": "https://storage.googleapis.com/signed-get-url",
        "content_type": "image/jpeg",
        "expires_in_seconds": 600,
    }
    with patch("auth_broker.main.create_read_url", return_value=fake_signed):
        async with AsyncClient(
            transport=ASGITransport(app=broker_app), base_url="http://test"
        ) as client:
            resp = await client.get("/prescriptions/mine-1/image-url")

    assert resp.status_code == 200
    body = resp.json()
    assert body["read_url"].startswith("https://")
    assert body["content_type"] == "image/jpeg"
    assert body["expires_in_seconds"] == 600
