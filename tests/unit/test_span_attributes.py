"""Unit tests for backend/app_utils/span_attributes.py."""
from __future__ import annotations

from app_utils.span_attributes import hash_patient_id, set_span_attributes


def test_hash_patient_id_is_stable_and_one_way():
    first = hash_patient_id("patient-abc")
    second = hash_patient_id("patient-abc")
    assert first == second
    assert first != "patient-abc"
    assert len(first) == 64


def test_hash_patient_id_empty_when_missing():
    assert hash_patient_id(None) == ""
    assert hash_patient_id("") == ""


def test_set_span_attributes_noop_without_recording_span():
    # Must not raise when no active recording span (local unit tests).
    set_span_attributes(agent_name="test", policy_decision="allow")
