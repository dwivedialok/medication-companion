"""Schema-level tests for Agent 1 ReaderOutput + ImageClassification.

The Gemini call itself is exercised in tests/integration; here we cover the
typed contract that the Policy Server gate depends on (Step 3a).
"""
from __future__ import annotations

import pytest

from agents.agent1_reader import (
    CONFIDENCE_THRESHOLD,
    ExtractedDrug,
    Gate1Reject,
    ImageClassification,
    ReaderOutput,
    create_reader_agent,
)


def test_image_classification_enum_values():
    assert {member.value for member in ImageClassification} == {
        "prescription",
        "non_prescription",
        "suspected_overlay_injection",
        "unreadable",
    }


def test_reader_output_defaults_to_prescription():
    output = ReaderOutput(status="ok")
    assert output.image_classification is ImageClassification.PRESCRIPTION
    assert output.extracted_drugs == []
    assert output.gate1_reject is None


def test_reader_output_accepts_string_classification():
    output = ReaderOutput(status="ok", image_classification="non_prescription")
    assert output.image_classification is ImageClassification.NON_PRESCRIPTION


def test_reader_output_rejects_unknown_classification():
    with pytest.raises(ValueError):
        ReaderOutput(status="ok", image_classification="totally_made_up")


def test_gate1_reject_default_message_has_consult_redirect():
    reject = Gate1Reject(reason="blurry")
    assert "doctor" in reject.user_message.lower()


def test_confidence_threshold_constant():
    # Spec value — tested so we notice if it drifts
    assert CONFIDENCE_THRESHOLD == 0.75


def test_extracted_drug_confidence_bounded():
    with pytest.raises(ValueError):
        ExtractedDrug(raw_name="Crocin", confidence=1.5)
    with pytest.raises(ValueError):
        ExtractedDrug(raw_name="Crocin", confidence=-0.1)


def test_create_reader_agent_accepts_callback():
    async def fake_cb(_ctx):
        return None

    agent = create_reader_agent(after_agent_callback=fake_cb)
    assert agent.after_agent_callback is fake_cb
    assert agent.name == "prescription_reader"


def test_create_reader_agent_default_no_callback():
    agent = create_reader_agent()
    assert agent.after_agent_callback is None
