"""Unit tests for backend/tools/pipeline_state.py."""
from __future__ import annotations

import pytest

from agents.agent1_reader import ExtractedDrug, ReaderOutput
from agents.agent2_resolver import ResolvedDrug, ResolverOutput
from tools.pipeline_state import (
    filter_resolver_to_allowlist,
    generics_from_resolved_state,
    normalized_raw_names,
    raw_names_from_reader_output,
    resolver_output_to_state,
    resolver_raw_on_allowlist,
)


def test_raw_names_from_reader_output():
    reader = ReaderOutput(
        status="ok",
        extracted_drugs=[
            ExtractedDrug(raw_name="GLIMISAVE 1 MG", confidence=0.9),
            ExtractedDrug(raw_name="SARTEL 80MG", confidence=0.88),
        ],
    )
    assert raw_names_from_reader_output(reader) == ["GLIMISAVE 1 MG", "SARTEL 80MG"]


def test_filter_resolver_drops_drugs_not_on_allowlist():
    allowed = ["GLIMISAVE 1 MG", "SARTEL 80MG"]
    output = ResolverOutput(
        resolved_drugs=[
            ResolvedDrug(
                raw_name="GLIMISAVE 1 MG",
                generic_name="glimepiride",
                tag="NEW",
                confidence=1.0,
            ),
            ResolvedDrug(
                raw_name="FAKE EXTRA DRUG",
                generic_name="metformin",
                tag="NEW",
                confidence=0.5,
            ),
        ],
        unresolved_count=0,
    )
    filtered = filter_resolver_to_allowlist(output, allowed)
    assert len(filtered.resolved_drugs) == 1
    assert filtered.resolved_drugs[0].generic_name == "glimepiride"


def test_generics_from_state_skips_unresolved():
    state = {
        "resolved_drugs": [
            {"raw_name": "A", "generic_name": "aspirin", "tag": "NEW", "confidence": 1.0},
            {"raw_name": "B", "generic_name": "unknown", "tag": "UNRESOLVED", "confidence": 0.0},
        ]
    }
    assert generics_from_resolved_state(state) == ["aspirin"]


def test_resolver_output_to_state_roundtrip():
    output = ResolverOutput(
        resolved_drugs=[
            ResolvedDrug(
                raw_name="Ecosprin",
                generic_name="aspirin",
                tag="NEW",
                confidence=1.0,
            )
        ],
        unresolved_count=0,
    )
    state_items = resolver_output_to_state(output)
    assert generics_from_resolved_state({"resolved_drugs": state_items}) == ["aspirin"]


def test_normalized_raw_names_strips_dose_tokens():
    keys = normalized_raw_names(["GLIMISAVE 1 MG", "SARTEL 80MG"])
    assert "glimisave" in keys
    assert "sartel" in keys


def test_filter_resolver_matches_ocr_line_to_short_brand():
    allowed = [
        "Tab Ecosprin 75 mg",
        "Tab Nise 100 mg",
        "Tab Warf 2 mg",
        "Tab Flagyl 400 mg",
    ]
    output = ResolverOutput(
        resolved_drugs=[
            ResolvedDrug(
                raw_name="Ecosprin",
                generic_name="aspirin",
                tag="NEW",
                confidence=1.0,
            ),
            ResolvedDrug(
                raw_name="Nise",
                generic_name="nimesulide",
                tag="NEW",
                confidence=1.0,
            ),
            ResolvedDrug(
                raw_name="Warf",
                generic_name="warfarin",
                tag="NEW",
                confidence=1.0,
            ),
            ResolvedDrug(
                raw_name="Flagyl",
                generic_name="metronidazole",
                tag="NEW",
                confidence=1.0,
            ),
        ],
        unresolved_count=0,
    )
    filtered = filter_resolver_to_allowlist(output, allowed)
    assert len(filtered.resolved_drugs) == 4


def test_resolver_raw_on_allowlist_token_overlap():
    assert resolver_raw_on_allowlist("Ecosprin", ["Tab Ecosprin 75 mg"])
    assert not resolver_raw_on_allowlist("FakeDrug", ["Tab Ecosprin 75 mg"])
