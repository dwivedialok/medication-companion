"""
backend/tools/drug_normalize.py

Pure functions for normalizing drug/brand strings before lookup.

Used by:
- scripts/build_drug_index.py at build time to canonicalize all keys
- backend/tools/drug_lookup.py at runtime to canonicalize incoming queries
- backend/tools/interaction_lookup.py for generic-pair canonicalization

Design goals:
- Deterministic, no I/O, no LLM.
- Lossless for the display form: callers preserve the raw string for UI,
  and use these helpers only for index/match keys.
"""
from __future__ import annotations

import re

_DOSE_TOKEN = re.compile(
    r"\b\d+(?:\.\d+)?\s*"
    r"(?:mg|mcg|g|ml|iu|i\.u\.|units?|%)"
    r"(?:\s*/\s*(?:\d+(?:\.\d+)?\s*)?(?:mg|mcg|g|ml|iu|i\.u\.|units?|%))?",
    re.IGNORECASE,
)
_TRAILING_NUM = re.compile(r"(?:\s+\d+(?:\.\d+)?)+\b")
_PAREN = re.compile(r"\([^)]*\)")
_NON_ALNUM = re.compile(r"[^a-z0-9+ ]+")
_MULTISPACE = re.compile(r"\s+")

_BRITISH_TO_US = {
    "amoxycillin": "amoxicillin",
    "cefuroxim": "cefuroxime",
    "paracetomol": "paracetamol",
    "salbutamol": "salbutamol",
}

_SALT_SUFFIXES = (
    "hydrochloride",
    "dihydrochloride",
    "hcl",
    "sodium",
    "potassium",
    "calcium",
    "sulphate",
    "sulfate",
    "phosphate",
    "maleate",
    "fumarate",
    "tartrate",
    "succinate",
    "besylate",
    "besilate",
    "mesylate",
    "citrate",
    "acetate",
    "gluconate",
    "lactate",
    "nitrate",
    "tosylate",
    "bromide",
    "chloride",
    "iodide",
)


def normalize_brand(name: str) -> str:
    """
    Normalize a brand name for index/match keys.

    Examples:
        "Augmentin 625 Duo Tablet" -> "augmentin duo tablet"
        "Azee 500"                 -> "azee"
        "Pantocid DSR"             -> "pantocid dsr"
    """
    if not name:
        return ""
    s = name.lower().strip()
    s = _PAREN.sub(" ", s)
    s = _DOSE_TOKEN.sub(" ", s)
    s = s.replace("+", " ")
    s = _NON_ALNUM.sub(" ", s)
    s = _MULTISPACE.sub(" ", s).strip()
    s = _TRAILING_NUM.sub("", s).strip()
    return s


def normalize_generic(name: str) -> str:
    """
    Normalize a single generic / salt name.

    - lowercase, whitespace-collapsed
    - dose tokens and parenthetical contents stripped
    - British/American spelling folded
    - common salt suffixes stripped (besylate, sodium, hydrochloride, ...)

    Examples:
        "Amoxycillin  (500mg)" -> "amoxicillin"
        "Amlodipine Besylate"  -> "amlodipine"
        "Insulin Isophane (40IU)" -> "insulin isophane"
    """
    if not name:
        return ""
    s = name.lower().strip()
    s = _PAREN.sub(" ", s)
    s = _DOSE_TOKEN.sub(" ", s)
    s = _NON_ALNUM.sub(" ", s)
    s = _MULTISPACE.sub(" ", s).strip()
    s = _BRITISH_TO_US.get(s, s)
    for suffix in _SALT_SUFFIXES:
        if s.endswith(" " + suffix):
            s = s[: -(len(suffix) + 1)].strip()
            break
    s = _BRITISH_TO_US.get(s, s)
    return s


def split_components(raw: str) -> list[tuple[str, str]]:
    """
    Split a composition string into [(generic_norm, dose), ...].

    Accepts either:
      - pipe-separated: "pantoprazole 40mg|domperidone 10mg"
      - plus-separated: "amoxicillin+clavulanate"
      - comma-separated: "Amoxycillin  (500mg) ,  Clavulanic Acid (125mg)"

    Dose is preserved verbatim from the source (e.g. "40mg", "500mcg")
    so downstream callers can display it; normalization only strips it
    from the matching key.
    """
    if not raw:
        return []
    if "|" in raw:
        parts = [p.strip() for p in raw.split("|") if p.strip()]
    elif "," in raw and "(" in raw:
        parts = [p.strip() for p in raw.split(",") if p.strip()]
    elif "+" in raw:
        parts = [p.strip() for p in raw.split("+") if p.strip()]
    else:
        parts = [raw.strip()]

    out: list[tuple[str, str]] = []
    for part in parts:
        dose_match = _DOSE_TOKEN.search(part)
        dose = dose_match.group(0).strip() if dose_match else ""
        generic = normalize_generic(part)
        if generic:
            out.append((generic, dose))
    return out


def canonical_pair(a: str, b: str) -> tuple[str, str]:
    """Sort a pair of normalized generics so (A,B) and (B,A) collapse to one key."""
    na, nb = normalize_generic(a), normalize_generic(b)
    return (na, nb) if na <= nb else (nb, na)


SEVERITY_MAP = {
    "HIGH": "HIGH",
    "INFO": "INFO",
    "LIFE-THREATENING": "HIGH",
    "LIFE THREATENING": "HIGH",
    "MAJOR": "HIGH",
    "SERIOUS": "HIGH",
    "MODERATE": "MODERATE",
    "MINOR": "LOW",
    "LOW": "LOW",
}


def map_severity(raw: str | None) -> str:
    """
    Map dataset severity strings to the project's hard-rule vocabulary
    (HIGH | MODERATE | LOW | INFO | NONE). Unknown values map to INFO.
    """
    if not raw:
        return "INFO"
    return SEVERITY_MAP.get(raw.strip().upper(), "INFO")
