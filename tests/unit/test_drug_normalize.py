"""Unit tests for backend/tools/drug_normalize.py."""
import pytest

from tools.drug_normalize import (
    canonical_pair,
    map_severity,
    normalize_brand,
    normalize_generic,
    split_components,
)


# ── normalize_brand ──────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Azee 500", "azee"),
        ("Augmentin 625 Duo Tablet", "augmentin duo tablet"),
        ("Pantocid DSR", "pantocid dsr"),
        ("PANTOCID DSR", "pantocid dsr"),
        ("  Pantocid   DSR  ", "pantocid dsr"),
        ("Insulin 40IU/ml Injection", "insulin injection"),
        ("Telma AM", "telma am"),
        ("", ""),
    ],
)
def test_normalize_brand(raw, expected):
    assert normalize_brand(raw) == expected


# ── normalize_generic ────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Amoxycillin  (500mg)", "amoxicillin"),
        ("Amoxicillin 500mg", "amoxicillin"),
        ("amoxycillin", "amoxicillin"),
        ("Amlodipine Besylate", "amlodipine"),
        ("Atorvastatin Calcium", "atorvastatin"),
        ("Metformin Hydrochloride", "metformin"),
        ("Pantoprazole Sodium", "pantoprazole"),
        ("Insulin Isophane (40IU)", "insulin isophane"),
        ("Clavulanic Acid (125mg)", "clavulanic acid"),
        ("", ""),
    ],
)
def test_normalize_generic(raw, expected):
    assert normalize_generic(raw) == expected


# ── split_components ─────────────────────────────────────────────────────────

def test_split_pipe():
    parts = split_components("pantoprazole 40mg|domperidone 10mg")
    assert parts == [("pantoprazole", "40mg"), ("domperidone", "10mg")]


def test_split_plus():
    parts = split_components("amoxicillin+clavulanate")
    assert parts == [("amoxicillin", ""), ("clavulanate", "")]


def test_split_comma_paren():
    parts = split_components("Amoxycillin  (500mg) ,  Clavulanic Acid (125mg)")
    assert parts == [("amoxicillin", "500mg"), ("clavulanic acid", "125mg")]


def test_split_empty():
    assert split_components("") == []
    assert split_components("   ") == []


# ── canonical_pair / severity ────────────────────────────────────────────────

def test_canonical_pair_sorts():
    assert canonical_pair("Warfarin", "Aspirin") == ("aspirin", "warfarin")
    assert canonical_pair("Aspirin", "Warfarin") == ("aspirin", "warfarin")


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("MAJOR", "HIGH"),
        ("major", "HIGH"),
        ("SERIOUS", "HIGH"),
        ("LIFE-THREATENING", "HIGH"),
        ("LIFE THREATENING", "HIGH"),
        ("MODERATE", "MODERATE"),
        ("MINOR", "LOW"),
        ("UNKNOWN", "INFO"),
        ("", "INFO"),
        (None, "INFO"),
    ],
)
def test_map_severity(raw, expected):
    assert map_severity(raw) == expected
