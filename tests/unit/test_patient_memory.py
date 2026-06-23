"""
Unit tests for backend/tools/patient_memory.py.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from agents.agent4_education import EducationOutput, InteractionCard
from memory.memory_service import MemoryServiceWrapper
from tools.patient_memory import (
    create_patient_history_tool,
    persist_visit_to_memory,
)


class FakeToolContext:
    def __init__(self, user_id: str):
        self.user_id = user_id


def _education_output() -> EducationOutput:
    return EducationOutput(
        drug_cards=[],
        interaction_cards=[
            InteractionCard(
                drug_pair="aspirin+nimesulide",
                severity="HIGH",
                plain_language="May increase bleeding risk.",
            )
        ],
        summary="Two high-severity interactions were found.",
        questions_for_doctor=["Can I take these together?"],
        overall_severity="HIGH",
    )


def _make_ctx(*, events: list, state: dict | None = None, user_id: str = "patient-1"):
    return SimpleNamespace(
        session=SimpleNamespace(id="sess-mem-1", events=events),
        user_id=user_id,
        state=state
        or {
            "resolved_drugs": [
                {"generic_name": "aspirin", "tag": "NEW"},
                {"generic_name": "warfarin", "tag": "NEW"},
            ]
        },
    )


@pytest.mark.asyncio
async def test_patient_history_tool_reads_memory():
    memory = MemoryServiceWrapper()
    await memory.save_visit("patient-1", ["warfarin"], "HIGH")
    tool = create_patient_history_tool(memory)

    history = await tool.func(FakeToolContext("patient-1"))
    assert len(history) == 1
    assert history[0]["resolved_drugs"] == ["warfarin"]


@pytest.mark.asyncio
async def test_patient_history_tool_returns_empty_for_new_patient():
    memory = MemoryServiceWrapper()
    tool = create_patient_history_tool(memory)

    history = await tool.func(FakeToolContext("new-patient"))
    assert history == []


@pytest.mark.asyncio
async def test_persist_visit_skips_gate1_reject():
    memory = MemoryServiceWrapper()
    events = [
        SimpleNamespace(
            author="prescription_reader",
            output={"status": "gate1_reject", "gate1_reject": {"reason": "bad"}},
        )
    ]
    ctx = _make_ctx(events=events)

    await persist_visit_to_memory(ctx, memory)

    assert await memory.get_medications_for_patient("patient-1") == []


@pytest.mark.asyncio
async def test_persist_visit_writes_from_session_events():
    memory = MemoryServiceWrapper()
    events = [
        SimpleNamespace(
            author="patient_education",
            output=_education_output().model_dump(),
        )
    ]
    ctx = _make_ctx(events=events, user_id="patient-write-1")

    await persist_visit_to_memory(ctx, memory)

    visits = await memory.get_medications_for_patient("patient-write-1")
    assert len(visits) == 1
    assert visits[0]["resolved_drugs"] == ["aspirin", "warfarin"]
    assert visits[0]["severity_summary"] == "HIGH"


@pytest.mark.asyncio
async def test_persist_visit_falls_back_to_safety_tool_generics():
    memory = MemoryServiceWrapper()
    events = [
        SimpleNamespace(
            author="patient_education",
            output=_education_output().model_dump(),
        ),
        SimpleNamespace(
            get_function_responses=lambda: [
                SimpleNamespace(
                    name="check_prescription_interactions",
                    response={
                        "current_generics": ["metronidazole", "warfarin"],
                        "interactions": [],
                    },
                )
            ]
        ),
    ]
    ctx = _make_ctx(events=events, state={"resolved_drugs": []}, user_id="patient-fallback")

    await persist_visit_to_memory(ctx, memory)

    visits = await memory.get_medications_for_patient("patient-fallback")
    assert visits[0]["resolved_drugs"] == ["metronidazole", "warfarin"]
