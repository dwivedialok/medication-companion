"""
Unit tests for backend/memory/session_service.py and memory/memory_service.py.
Run from backend/ dir: pytest tests/test_memory_services.py -v
All tests use MEMORY_BACKEND=local (no GCP credentials required).
"""
import os

import pytest

os.environ.setdefault("MEMORY_BACKEND", "local")
os.environ.setdefault("ENVIRONMENT", "local")


# ── Session service factory ───────────────────────────────────────────────────

def test_session_service_factory_returns_in_memory_in_local_mode(monkeypatch):
    monkeypatch.setenv("MEMORY_BACKEND", "local")
    from memory.session_service import create_session_service
    from google.adk.sessions import InMemorySessionService

    svc = create_session_service()
    assert isinstance(svc, InMemorySessionService)


def test_session_service_factory_local_does_not_need_gcp_env(monkeypatch):
    monkeypatch.setenv("MEMORY_BACKEND", "local")
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("AGENT_RUNTIME_ID", raising=False)

    from memory.session_service import create_session_service
    # Should not raise even without GCP vars
    svc = create_session_service()
    assert svc is not None


# ── Memory service factory ────────────────────────────────────────────────────

def test_memory_service_factory_local_mode(monkeypatch):
    monkeypatch.setenv("MEMORY_BACKEND", "local")
    from memory.memory_service import create_memory_service, MemoryServiceWrapper

    svc = create_memory_service()
    assert isinstance(svc, MemoryServiceWrapper)
    assert svc.is_local() is True


def test_memory_service_factory_local_no_gcp_env(monkeypatch):
    monkeypatch.setenv("MEMORY_BACKEND", "local")
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)

    from memory.memory_service import create_memory_service
    svc = create_memory_service()
    assert svc is not None


# ── Memory CRUD ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_empty_history_returns_empty_list():
    from memory.memory_service import MemoryServiceWrapper
    svc = MemoryServiceWrapper()
    result = await svc.get_medications_for_patient("patient-001")
    assert result == []


@pytest.mark.asyncio
async def test_save_and_retrieve_visit():
    from memory.memory_service import MemoryServiceWrapper
    svc = MemoryServiceWrapper()

    await svc.save_visit(
        patient_id="patient-001",
        resolved_drug_names=["azithromycin", "paracetamol"],
        severity="LOW",
    )
    history = await svc.get_medications_for_patient("patient-001")

    assert len(history) == 1
    visit = history[0]
    assert visit["resolved_drugs"] == ["azithromycin", "paracetamol"]
    assert visit["severity_summary"] == "LOW"
    assert "visit_timestamp" in visit


@pytest.mark.asyncio
async def test_multiple_visits_accumulated():
    from memory.memory_service import MemoryServiceWrapper
    svc = MemoryServiceWrapper()

    await svc.save_visit("p1", ["warfarin"], "HIGH")
    await svc.save_visit("p1", ["aspirin", "clopidogrel"], "MODERATE")

    history = await svc.get_medications_for_patient("p1")
    assert len(history) == 2


@pytest.mark.asyncio
async def test_patients_are_isolated():
    from memory.memory_service import MemoryServiceWrapper
    svc = MemoryServiceWrapper()

    await svc.save_visit("patient-A", ["metformin"], "INFO")
    history_b = await svc.get_medications_for_patient("patient-B")

    assert history_b == []


@pytest.mark.asyncio
async def test_visit_stores_only_allowed_fields():
    from memory.memory_service import MemoryServiceWrapper
    svc = MemoryServiceWrapper()

    await svc.save_visit("p1", ["lisinopril"], "NONE")
    visits = await svc.get_medications_for_patient("p1")
    visit = visits[0]

    allowed_keys = {"visit_timestamp", "resolved_drugs", "severity_summary"}
    assert set(visit.keys()) == allowed_keys


@pytest.mark.asyncio
async def test_visit_does_not_store_image_data():
    """Memory must never store image data even if accidentally passed."""
    from memory.memory_service import MemoryServiceWrapper
    svc = MemoryServiceWrapper()

    # save_visit signature only accepts drug names and severity — no image param
    await svc.save_visit("p1", ["atenolol"], "LOW")
    visits = await svc.get_medications_for_patient("p1")
    visit_str = str(visits[0])

    assert "image" not in visit_str.lower()
    assert "base64" not in visit_str.lower()


@pytest.mark.asyncio
async def test_resolved_drugs_stored_as_list():
    from memory.memory_service import MemoryServiceWrapper
    svc = MemoryServiceWrapper()

    drugs = ["amlodipine", "ramipril", "rosuvastatin"]
    await svc.save_visit("p1", drugs, "INFO")
    visits = await svc.get_medications_for_patient("p1")

    assert isinstance(visits[0]["resolved_drugs"], list)
    assert visits[0]["resolved_drugs"] == drugs


@pytest.mark.asyncio
async def test_timestamp_is_iso_format():
    from memory.memory_service import MemoryServiceWrapper
    from datetime import datetime
    svc = MemoryServiceWrapper()

    await svc.save_visit("p1", ["metoprolol"], "NONE")
    visits = await svc.get_medications_for_patient("p1")
    ts = visits[0]["visit_timestamp"]

    # Should parse without error
    parsed = datetime.fromisoformat(ts)
    assert parsed is not None


@pytest.mark.asyncio
async def test_get_returns_copy_not_reference():
    """Mutations to returned list should not affect stored history."""
    from memory.memory_service import MemoryServiceWrapper
    svc = MemoryServiceWrapper()

    await svc.save_visit("p1", ["warfarin"], "HIGH")
    history = await svc.get_medications_for_patient("p1")
    history.clear()

    history2 = await svc.get_medications_for_patient("p1")
    assert len(history2) == 1


# ── Severity values ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("severity", ["HIGH", "MODERATE", "LOW", "INFO", "NONE"])
async def test_all_valid_severity_values(severity):
    from memory.memory_service import MemoryServiceWrapper
    svc = MemoryServiceWrapper()

    await svc.save_visit("p1", ["drug-a"], severity)
    visits = await svc.get_medications_for_patient("p1")
    assert visits[0]["severity_summary"] == severity
