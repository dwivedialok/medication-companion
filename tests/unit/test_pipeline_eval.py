"""Unit tests for backend/evaluation/pipeline_eval.py."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from agents.agent4_education import EducationOutput, InteractionCard
from evaluation.pipeline_eval import schedule_pipeline_eval


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


def _make_ctx(*, events: list, state: dict | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        session=SimpleNamespace(id="sess-eval-1", events=events),
        user_id="patient-eval-1",
        state=state or {
            "resolved_drugs": [
                {"generic_name": "aspirin", "tag": "NEW"},
                {"generic_name": "nimesulide", "tag": "NEW"},
            ]
        },
    )


@pytest.mark.asyncio
async def test_schedule_pipeline_eval_skips_gate1_reject():
    events = [
        SimpleNamespace(
            author="prescription_reader",
            output={"status": "gate1_reject", "gate1_reject": {"reason": "bad"}},
        )
    ]
    ctx = _make_ctx(events=events)
    with patch(
        "evaluation.pipeline_eval.asyncio.create_task",
    ) as create_task:
        await schedule_pipeline_eval(ctx)
        create_task.assert_not_called()


@pytest.mark.asyncio
async def test_schedule_pipeline_eval_schedules_on_success():
    education = _education_output()
    events = [
        SimpleNamespace(
            author="patient_education",
            output=education.model_dump(),
        ),
        SimpleNamespace(
            get_function_responses=lambda: [
                SimpleNamespace(
                    name="check_prescription_interactions",
                    response={
                        "interactions": [
                            {
                                "drug_a": "aspirin",
                                "drug_b": "nimesulide",
                                "severity": "HIGH",
                            }
                        ]
                    },
                )
            ]
        ),
    ]
    ctx = _make_ctx(events=events)
    with patch(
        "evaluation.pipeline_eval.asyncio.create_task",
    ) as create_task:
        await schedule_pipeline_eval(ctx)
        create_task.assert_called_once()
