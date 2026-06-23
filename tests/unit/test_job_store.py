"""Unit tests for prescription job store."""
import pytest

from auth_broker.job_store import MemoryJobStore
from schemas import JobError, PrescriptionResult, ResolvedDrug


@pytest.fixture
def store():
    return MemoryJobStore()


@pytest.mark.asyncio
async def test_create_and_get_job(store):
    job = await store.create_job(
        job_id="job-1",
        patient_id="p-1",
        gcs_uri="gs://b/prescriptions/p-1/x.jpg",
        language="en-IN",
        content_type="image/jpeg",
    )
    assert job.status == "pending"
    fetched = await store.get_job("job-1")
    assert fetched is not None
    assert fetched.patient_id == "p-1"


@pytest.mark.asyncio
async def test_set_result_marks_done(store):
    await store.create_job(
        job_id="job-2",
        patient_id="p-1",
        gcs_uri="gs://b/prescriptions/p-1/x.jpg",
        language="en-IN",
        content_type="image/jpeg",
    )
    result = PrescriptionResult(
        session_id="sess-1",
        resolved_drugs=[
            ResolvedDrug(raw_name="X", generic_name="x", tag="NEW"),
        ],
        interactions=[],
        overall_severity="NONE",
        explanation_en="Summary. Please discuss this with your doctor or pharmacist.",
        explanation_localised="Summary.",
        audio_url="",
        doctor_questions=[],
        disclaimer="Please discuss this with your doctor or pharmacist.",
    )
    await store.set_result("job-2", result)
    job = await store.get_job("job-2")
    assert job is not None
    assert job.status == "done"
    assert job.result is not None
    assert job.result.session_id == "sess-1"


@pytest.mark.asyncio
async def test_set_failed_marks_failed(store):
    await store.create_job(
        job_id="job-3",
        patient_id="p-1",
        gcs_uri="gs://b/prescriptions/p-1/x.jpg",
        language="en-IN",
        content_type="image/jpeg",
    )
    await store.set_failed(
        "job-3",
        JobError(code="gate1_reject", message="Retake", reason="unreadable"),
    )
    job = await store.get_job("job-3")
    assert job is not None
    assert job.status == "failed"
    assert job.error is not None
    assert job.error.code == "gate1_reject"
