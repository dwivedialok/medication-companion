"""
backend/tools/drug_lookup.py
FunctionTool: brand name → generic name lookup.

Lookup order:
  1. bundled data/india_brands.csv (always — fast, covers Indian brands)
  2. RxNav REST API (skipped when ENVIRONMENT=local)
  3. UNRESOLVED tag if neither source succeeds
"""
import csv
import logging
import os
from pathlib import Path

import httpx
from google.adk.tools import FunctionTool

logger = logging.getLogger(__name__)

_CSV_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "india_brands.csv"

_INDIA_BRANDS: dict[str, dict] | None = None


def _load_csv() -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    try:
        with open(_CSV_PATH, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                key = row["brand_name"].strip().lower()
                lookup[key] = {
                    "generic": row["generic_name"].strip().lower(),
                    "components": row["components"].strip(),
                    "drug_class": row["drug_class"].strip(),
                }
    except FileNotFoundError:
        logger.warning("india_brands.csv not found at %s", _CSV_PATH)
    return lookup


def _brands() -> dict[str, dict]:
    global _INDIA_BRANDS
    if _INDIA_BRANDS is None:
        _INDIA_BRANDS = _load_csv()
    return _INDIA_BRANDS


def _rxnav_lookup(brand_name: str) -> dict | None:
    """Call RxNav synchronously; returns None on miss or error."""
    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.get(
                "https://rxnav.nlm.nih.gov/REST/rxcui.json",
                params={"name": brand_name, "search": "1"},
            )
            r.raise_for_status()
            ids = r.json().get("idGroup", {}).get("rxnormId") or []
            if not ids:
                return None
            rxcui = ids[0]
            r2 = client.get(
                f"https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}/property.json",
                params={"propName": "RxNorm Name"},
            )
            r2.raise_for_status()
            concepts = (
                r2.json().get("propConceptGroup", {}).get("propConcept") or []
            )
            generic = concepts[0].get("propValue", "").lower() if concepts else ""
            if generic:
                return {"generic": generic, "drug_class": "", "confidence": 0.85}
    except Exception as exc:
        logger.debug("RxNav lookup failed for %s: %s", brand_name, exc)
    return None


def drug_lookup(brand_name: str) -> dict:
    """
    Resolve a drug brand name to its generic name and drug class.

    Args:
        brand_name: Drug brand name as read from the prescription
                    (e.g. "Azee", "Pantocid DSR", "Augmentin").

    Returns:
        dict with keys:
          generic (str)       — lowercase generic name
          drug_class (str)    — pharmacological class or ""
          confidence (float)  — 0.0–1.0
          source (str)        — "rxnav" | "csv" | "unresolved"
    """
    key = brand_name.strip().lower()

    # 1. CSV lookup — always first, covers Indian brands and FDCs
    entry = _brands().get(key)
    if entry:
        return {
            "generic": entry["generic"],
            "drug_class": entry["drug_class"],
            "confidence": 1.0,
            "source": "csv",
        }

    # 2. RxNav — skip in local/test mode to avoid network dependency
    if os.getenv("ENVIRONMENT", "development") != "local":
        result = _rxnav_lookup(brand_name)
        if result:
            return {**result, "source": "rxnav"}

    # 3. Unresolved
    return {
        "generic": brand_name.lower(),
        "drug_class": "",
        "confidence": 0.0,
        "source": "unresolved",
    }


drug_lookup_tool = FunctionTool(drug_lookup)
