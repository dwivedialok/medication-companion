"""
Unit tests for backend/tools/combo_splitter.py.
Run from backend/ dir: pytest tests/test_combo_splitter.py -v
"""
import pytest


def _reset_cache():
    import tools.combo_splitter as m
    m._COMBO_MAP = None


@pytest.fixture(autouse=True)
def reset_cache():
    _reset_cache()
    yield
    _reset_cache()


# ── FDC splitting ─────────────────────────────────────────────────────────────

def test_split_pantocid_dsr():
    from tools.combo_splitter import combo_splitter
    result = combo_splitter("Pantocid DSR")
    assert len(result) == 2
    components = {c["component"] for c in result}
    assert "pantoprazole" in components
    assert "domperidone" in components


def test_split_pantocid_dsr_doses():
    from tools.combo_splitter import combo_splitter
    result = combo_splitter("Pantocid DSR")
    by_comp = {c["component"]: c["dose"] for c in result}
    assert by_comp["pantoprazole"] == "40mg"
    assert by_comp["domperidone"] == "10mg"


def test_split_combiflam():
    from tools.combo_splitter import combo_splitter
    result = combo_splitter("Combiflam")
    assert len(result) == 2
    components = {c["component"] for c in result}
    assert "ibuprofen" in components
    assert "paracetamol" in components


def test_split_cheston_cold_three_components():
    from tools.combo_splitter import combo_splitter
    result = combo_splitter("Cheston Cold")
    assert len(result) == 3
    components = {c["component"] for c in result}
    assert "cetirizine" in components
    assert "paracetamol" in components
    assert "pseudoephedrine" in components


def test_split_augmentin():
    from tools.combo_splitter import combo_splitter
    result = combo_splitter("Augmentin")
    assert len(result) == 2
    components = {c["component"] for c in result}
    assert "amoxicillin" in components
    assert "clavulanate" in components


def test_split_akurit_four_components():
    """Antitubercular FDC with 4 components."""
    from tools.combo_splitter import combo_splitter
    result = combo_splitter("Akurit 4")
    assert len(result) == 4


# ── Non-FDC returns empty list ────────────────────────────────────────────────

def test_not_a_combo_azee():
    from tools.combo_splitter import combo_splitter
    result = combo_splitter("Azee")
    assert result == []


def test_not_a_combo_glycomet():
    from tools.combo_splitter import combo_splitter
    result = combo_splitter("Glycomet")
    assert result == []


def test_not_a_combo_ecosprin():
    from tools.combo_splitter import combo_splitter
    result = combo_splitter("Ecosprin")
    assert result == []


def test_unknown_drug_returns_empty():
    from tools.combo_splitter import combo_splitter
    result = combo_splitter("CompletelyUnknownXYZ9999")
    assert result == []


# ── Case insensitivity ────────────────────────────────────────────────────────

def test_case_insensitive_brand():
    from tools.combo_splitter import combo_splitter
    lower = combo_splitter("pantocid dsr")
    upper = combo_splitter("PANTOCID DSR")
    mixed = combo_splitter("Pantocid DSR")
    assert lower == mixed
    assert upper == mixed


# ── Return type always a list ─────────────────────────────────────────────────

@pytest.mark.parametrize("drug", ["Pantocid DSR", "Azee", "UnknownXYZ"])
def test_always_returns_list(drug):
    from tools.combo_splitter import combo_splitter
    result = combo_splitter(drug)
    assert isinstance(result, list)


def test_each_component_has_required_keys():
    from tools.combo_splitter import combo_splitter
    result = combo_splitter("Combiflam")
    for item in result:
        assert "component" in item
        assert "dose" in item


# ── Tool wrapper ──────────────────────────────────────────────────────────────

def test_combo_splitter_tool_is_function_tool():
    from google.adk.tools import FunctionTool
    from tools.combo_splitter import combo_splitter_tool
    assert isinstance(combo_splitter_tool, FunctionTool)
