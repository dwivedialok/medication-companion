"""Unit tests for backend/evaluation/llm_judge.py."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from evaluation.llm_judge import _parse_judge_json, score_pipeline_output


def test_parse_judge_json_strips_fence():
    raw = '```json\n{"score": 8, "flags": ["ok"]}\n```'
    assert _parse_judge_json(raw) == {"score": 8, "flags": ["ok"]}


@pytest.mark.asyncio
async def test_score_pipeline_output_uses_genai_client():
    mock_response = MagicMock()
    mock_response.text = '{"score": 9, "flags": []}'

    with patch("evaluation.llm_judge._generate_judge_json", return_value={"score": 9, "flags": []}):
        score = await score_pipeline_output(
            session_id="sess-1",
            patient_id="patient-1",
            resolved_drugs=["aspirin"],
            interactions_found=[],
            explanation_text="Plain explanation.",
            agent_versions={"prescription_reader": "gemini-test"},
        )

    assert score.safety_score == 9
    assert score.clarity_score == 9
    assert score.flags == []
