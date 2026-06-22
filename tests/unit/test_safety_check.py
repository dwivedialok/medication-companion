"""Unit tests for backend/tools/safety_check.py."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from tools.safety_check import compute_prescription_safety


def test_compute_safety_no_generics():
    result = compute_prescription_safety([], [])
    assert result["interactions"] == []
    assert result["overall_severity"] == "NONE"
    assert result["safe_to_proceed"] is True
    assert result["pairs_checked"] == 0


def test_compute_safety_pair_count_within_visit():
    with patch("tools.safety_check.interaction_lookup") as mock_lookup:
        mock_lookup.return_value = {
            "severity": "NONE",
            "mechanism": "",
            "source": "none",
            "generic_a": "a",
            "generic_b": "b",
        }
        result = compute_prescription_safety(
            ["drug_a", "drug_b", "drug_c"],
            [],
        )
    assert result["pairs_checked"] == 3
    assert mock_lookup.call_count == 3


def test_compute_safety_emits_only_dataset_hits():
    def _lookup(a: str, b: str) -> dict:
        if {a, b} == {"aspirin", "warfarin"}:
            return {
                "severity": "HIGH",
                "mechanism": "Increased bleeding risk.",
                "source": "dataset",
                "generic_a": "aspirin",
                "generic_b": "warfarin",
            }
        return {
            "severity": "NONE",
            "mechanism": "",
            "source": "none",
            "generic_a": a,
            "generic_b": b,
        }

    with patch("tools.safety_check.interaction_lookup", side_effect=_lookup):
        result = compute_prescription_safety(
            ["aspirin", "paracetamol"],
            [{"resolved_drugs": ["warfarin"], "severity_summary": "MODERATE"}],
        )

    assert len(result["interactions"]) == 1
    hit = result["interactions"][0]
    assert hit["severity"] == "HIGH"
    assert hit["source"] == "cross_visit"
    assert hit["drug_a"] in ("aspirin", "warfarin")
    assert result["overall_severity"] == "HIGH"
    assert result["safe_to_proceed"] is False


def test_compute_safety_skips_duplicate_cross_visit_pair():
    with patch("tools.safety_check.interaction_lookup") as mock_lookup:
        mock_lookup.return_value = {
            "severity": "NONE",
            "mechanism": "",
            "source": "none",
            "generic_a": "aspirin",
            "generic_b": "aspirin",
        }
        result = compute_prescription_safety(
            ["aspirin"],
            [{"resolved_drugs": ["aspirin"]}],
        )
    assert result["pairs_checked"] == 0
    assert mock_lookup.call_count == 0
