"""Unit tests for backend/tools/interaction_lookup.py.

These tests assume data/drugs.db has been built by
scripts/build_drug_index.py. If the DB is missing the lookup
must still return NONE without crashing.
"""
import sqlite3
from pathlib import Path

import pytest

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "drugs.db"


@pytest.fixture(autouse=True)
def _reset_index():
    from tools import drug_index
    drug_index.reset()
    yield
    drug_index.reset()


def _known_pair() -> tuple[str, str, str] | None:
    """Return any (generic_a, generic_b, severity) row from the DB, or None."""
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    cur = conn.execute(
        "SELECT generic_a, generic_b, severity FROM interactions "
        "WHERE severity IN ('HIGH','MODERATE') LIMIT 1"
    )
    row = cur.fetchone()
    conn.close()
    return row


def test_unknown_pair_returns_none_severity():
    from tools.interaction_lookup import interaction_lookup
    result = interaction_lookup("__not_a_drug_a__", "__not_a_drug_b__")
    assert result["severity"] == "NONE"
    assert result["source"] == "none"


def test_same_drug_returns_none():
    from tools.interaction_lookup import interaction_lookup
    result = interaction_lookup("aspirin", "aspirin")
    assert result["severity"] == "NONE"


def test_empty_inputs_return_none():
    from tools.interaction_lookup import interaction_lookup
    assert interaction_lookup("", "aspirin")["severity"] == "NONE"
    assert interaction_lookup("aspirin", "")["severity"] == "NONE"


def test_known_pair_returns_dataset_severity():
    pair = _known_pair()
    if pair is None:
        pytest.skip("drugs.db not built or no interactions present")
    a, b, sev = pair
    from tools.interaction_lookup import interaction_lookup
    result = interaction_lookup(a, b)
    assert result["source"] == "dataset"
    assert result["severity"] == sev
    assert result["severity"] in ("HIGH", "MODERATE", "LOW", "INFO")


def test_pair_is_order_independent():
    pair = _known_pair()
    if pair is None:
        pytest.skip("drugs.db not built or no interactions present")
    a, b, _ = pair
    from tools.interaction_lookup import interaction_lookup
    fwd = interaction_lookup(a, b)
    rev = interaction_lookup(b, a)
    assert fwd["severity"] == rev["severity"]
    assert fwd["source"] == rev["source"]


def test_tool_wrapper_is_function_tool():
    from google.adk.tools import FunctionTool
    from tools.interaction_lookup import interaction_lookup_tool
    assert isinstance(interaction_lookup_tool, FunctionTool)
