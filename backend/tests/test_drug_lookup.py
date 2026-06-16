"""
Unit tests for backend/tools/drug_lookup.py.
Run from backend/ dir: pytest tests/test_drug_lookup.py -v
All tests use ENVIRONMENT=local so no network calls are made.
"""
import os

import pytest

os.environ.setdefault("ENVIRONMENT", "local")
os.environ.setdefault("MEMORY_BACKEND", "local")


def _reset_cache():
    import tools.drug_lookup as m
    m._INDIA_BRANDS = None


@pytest.fixture(autouse=True)
def reset_cache():
    _reset_cache()
    yield
    _reset_cache()


# ── Happy path ────────────────────────────────────────────────────────────────

def test_lookup_known_indian_brand():
    from tools.drug_lookup import drug_lookup
    result = drug_lookup("Azee")
    assert result["generic"] == "azithromycin"
    assert result["source"] == "csv"
    assert result["confidence"] == 1.0
    assert result["drug_class"] != ""


def test_lookup_augmentin():
    from tools.drug_lookup import drug_lookup
    result = drug_lookup("Augmentin")
    assert "amoxicillin" in result["generic"]
    assert result["source"] == "csv"


def test_lookup_combo_returns_combined_generic():
    from tools.drug_lookup import drug_lookup
    result = drug_lookup("Pantocid DSR")
    assert result["source"] == "csv"
    assert result["confidence"] == 1.0
    assert "pantoprazole" in result["generic"]


def test_lookup_ecosprin():
    from tools.drug_lookup import drug_lookup
    result = drug_lookup("Ecosprin")
    assert result["generic"] == "aspirin"
    assert result["source"] == "csv"


def test_lookup_deplatt():
    from tools.drug_lookup import drug_lookup
    result = drug_lookup("Deplatt")
    assert result["generic"] == "clopidogrel"
    assert result["source"] == "csv"


# ── UNRESOLVED path ───────────────────────────────────────────────────────────

def test_lookup_unknown_returns_unresolved():
    from tools.drug_lookup import drug_lookup
    result = drug_lookup("CompletelyUnknownXYZ9999")
    assert result["source"] == "unresolved"
    assert result["confidence"] == 0.0


def test_unresolved_preserves_input_as_generic():
    from tools.drug_lookup import drug_lookup
    result = drug_lookup("FakeDrug")
    assert result["generic"] == "fakedrug"


# ── Case insensitivity ────────────────────────────────────────────────────────

def test_lookup_lowercase():
    from tools.drug_lookup import drug_lookup
    result = drug_lookup("azee")
    assert result["source"] == "csv"
    assert result["generic"] == "azithromycin"


def test_lookup_uppercase():
    from tools.drug_lookup import drug_lookup
    result = drug_lookup("AZEE")
    assert result["source"] == "csv"


def test_lookup_mixed_case():
    from tools.drug_lookup import drug_lookup
    result = drug_lookup("AzEe")
    assert result["source"] == "csv"


# ── RxNav skipped in local mode ───────────────────────────────────────────────

def test_rxnav_not_called_in_local_mode(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "local")
    import tools.drug_lookup as module

    called = []

    def mock_rxnav(name: str):
        called.append(name)
        return None

    monkeypatch.setattr(module, "_rxnav_lookup", mock_rxnav)
    module.drug_lookup("CompletelyUnknownXYZ9999")
    assert len(called) == 0, "RxNav must not be called in local mode"


def test_rxnav_called_in_non_local_mode(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    import tools.drug_lookup as module

    called = []

    def mock_rxnav(name: str):
        called.append(name)
        return None

    monkeypatch.setattr(module, "_rxnav_lookup", mock_rxnav)
    module.drug_lookup("CompletelyUnknownXYZ9999")
    assert len(called) == 1


# ── Tool wrapper ──────────────────────────────────────────────────────────────

def test_drug_lookup_tool_is_function_tool():
    from google.adk.tools import FunctionTool
    from tools.drug_lookup import drug_lookup_tool
    assert isinstance(drug_lookup_tool, FunctionTool)


# ── Output schema keys always present ────────────────────────────────────────

@pytest.mark.parametrize("brand", ["Azee", "Glycomet", "UnknownXYZ"])
def test_output_always_has_required_keys(brand):
    from tools.drug_lookup import drug_lookup
    result = drug_lookup(brand)
    for key in ("generic", "drug_class", "confidence", "source"):
        assert key in result, f"Missing key '{key}' for input '{brand}'"
