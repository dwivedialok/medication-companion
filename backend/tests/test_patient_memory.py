"""
Unit tests for backend/tools/patient_memory.py.
Run from backend/ dir: pytest tests/test_patient_memory.py -v
"""
import pytest

from memory.memory_service import MemoryServiceWrapper
from tools.patient_memory import create_patient_history_tool


class FakeToolContext:
    def __init__(self, user_id: str):
        self.user_id = user_id


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
