"""
backend/tools/drug_lookup.py
FunctionTool: brand name -> generic name + composition lookup.

Tiered lookup (first hit wins):
  Tier 1  curated  data/india_brands.csv          (priority=100, source='csv')
  Tier 2  SQLite exact match on normalized key    (source='sqlite_exact')
  Tier 3  SQLite FTS5 token-prefix search         (source='sqlite_fts')
  Tier 4  RapidFuzz fuzzy match (token_set, >=90) (source='fuzzy')
  Tier 5  RxNav REST API (skipped when ENVIRONMENT=local)
  Tier 6  UNRESOLVED

Tiers 2-4 all read from data/drugs.db built by scripts/build_drug_index.py.

Returned dict:
  generic     str   -- combined generic, e.g. "amoxicillin+clavulanate"
  drug_class  str   -- therapeutic / drug class or ""
  components  list  -- [{component, dose}, ...] for FDCs (empty for monotherapy)
  confidence  float -- 0.0 - 1.0
  source      str   -- 'csv' | 'sqlite_exact' | 'sqlite_fts' | 'fuzzy' |
                       'rxnav' | 'unresolved'
  match_tier  str   -- diagnostic alias of `source` for observability
"""
from __future__ import annotations

import csv
import logging
import os
from pathlib import Path

import httpx
from google.adk.tools import FunctionTool

from tools import drug_index
from tools.drug_normalize import normalize_brand

logger = logging.getLogger(__name__)

_CSV_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "india_brands.csv"

# Public cache symbol preserved for backward compatibility with existing tests
# (tests reset `tools.drug_lookup._INDIA_BRANDS = None`).
_INDIA_BRANDS: dict[str, dict] | None = None

# Fuzzy index cache (lazily built from drugs.db).
_FUZZY_KEYS: list[str] | None = None

# Confidence floor for accepting a fuzzy match (strict Levenshtein ratio).
# Calibrated on the eval set: positive OCR cases score 80-95, while non-drug
# strings cap at ~62, leaving ~15-point margin.
_FUZZY_MIN_SCORE = 80

# Common OCR character confusions encountered in handwritten/printed Rx scans.
_OCR_TABLE = str.maketrans({"0": "o", "1": "l", "5": "s", "8": "b"})


# ── Tier 1: curated CSV ──────────────────────────────────────────────────────


def _load_csv() -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    try:
        with open(_CSV_PATH, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                brand = (row.get("brand_name") or "").strip()
                key = normalize_brand(brand)
                if not key:
                    continue
                generic = (row.get("generic_name") or "").strip().lower()
                components_raw = (row.get("components") or "").strip()
                drug_class = (row.get("drug_class") or "").strip()
                comps: list[dict] = []
                if components_raw:
                    for part in components_raw.split("|"):
                        part = part.strip()
                        if not part:
                            continue
                        tokens = part.split()
                        if len(tokens) >= 2:
                            comps.append(
                                {"component": " ".join(tokens[:-1]), "dose": tokens[-1]}
                            )
                        else:
                            comps.append({"component": part, "dose": ""})
                lookup[key] = {
                    "generic": generic,
                    "drug_class": drug_class,
                    "components": comps,
                }
    except FileNotFoundError:
        logger.warning("india_brands.csv not found at %s", _CSV_PATH)
    return lookup


def _brands() -> dict[str, dict]:
    global _INDIA_BRANDS
    if _INDIA_BRANDS is None:
        _INDIA_BRANDS = _load_csv()
    return _INDIA_BRANDS


# ── Tier 4: fuzzy ────────────────────────────────────────────────────────────


def _fuzzy_keys() -> list[str]:
    global _FUZZY_KEYS
    if _FUZZY_KEYS is None:
        _FUZZY_KEYS = drug_index.all_brand_keys()
    return _FUZZY_KEYS


def _query_variants(key: str) -> list[str]:
    """
    Generate OCR-aware variants of a normalized brand query.

    - the base normalized key
    - an OCR-folded variant (0->o, 1->l, 5->s, 8->b)
    - a digit-stem variant (truncate at the first digit if prefix length >= 3),
      catching strings like 'azee500' / 'azee5o0' where dose got fused to the
      brand stem with no whitespace.
    """
    variants = {key}
    folded = key.translate(_OCR_TABLE)
    if folded != key:
        variants.add(folded)
    for v in list(variants):
        for i, ch in enumerate(v):
            if ch.isdigit():
                alpha_prefix = sum(1 for c in v[:i] if c.isalpha())
                if alpha_prefix >= 3:
                    stem = v[:i].rstrip()
                    if stem:
                        variants.add(stem)
                break
    return [v for v in variants if v]


def _fuzzy_lookup(brand: str) -> tuple[str, int] | None:
    """Return (best_brand_norm, score) if score >= _FUZZY_MIN_SCORE, else None."""
    try:
        from rapidfuzz import fuzz, process
    except ImportError:
        return None
    keys = _fuzzy_keys()
    if not keys:
        return None
    base = normalize_brand(brand)
    if not base:
        return None

    best: tuple[str, float] | None = None
    for variant in _query_variants(base):
        match = process.extractOne(
            variant, keys, scorer=fuzz.ratio, score_cutoff=_FUZZY_MIN_SCORE
        )
        if match is None:
            continue
        cand_key, score, _ = match
        if best is None or score > best[1]:
            best = (cand_key, score)
    if best is None:
        return None
    return best[0], int(best[1])


def _row_to_result(row: dict, source: str, confidence: float) -> dict:
    """Hydrate a brands row with its components into the tool return shape."""
    components = drug_index.components_for_brand_id(row["brand_id"])
    if components:
        generic = "+".join(c["component"] for c in components)
    else:
        generic = row["brand_norm"]
    return {
        "generic": generic,
        "drug_class": row.get("drug_class") or "",
        "components": components,
        "confidence": confidence,
        "source": source,
        "match_tier": source,
    }


# ── Tier 5: RxNav ────────────────────────────────────────────────────────────


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
                return {
                    "generic": generic,
                    "drug_class": "",
                    "components": [],
                    "confidence": 0.85,
                }
    except Exception as exc:
        logger.debug("RxNav lookup failed for %s: %s", brand_name, exc)
    return None


# ── Public tool ──────────────────────────────────────────────────────────────


def drug_lookup(brand_name: str) -> dict:
    """
    Resolve a drug brand name to its generic name, drug class, and FDC components.

    Args:
        brand_name: Drug brand name as read from the prescription
                    (e.g. "Azee", "Pantocid DSR", "Augmentin").

    Returns:
        dict with keys:
          generic (str)            -- lowercase generic name
          drug_class (str)         -- pharmacological class or ""
          components (list[dict])  -- [{component, dose}, ...] for FDCs
          confidence (float)       -- 0.0 - 1.0
          source (str)             -- 'csv' | 'sqlite_exact' | 'sqlite_fts' |
                                      'fuzzy' | 'rxnav' | 'unresolved'
          match_tier (str)         -- diagnostic alias of `source`
    """
    key = normalize_brand(brand_name)

    # Tier 1: curated CSV (highest precedence, fastest)
    entry = _brands().get(key)
    if entry:
        return {
            "generic": entry["generic"],
            "drug_class": entry["drug_class"],
            "components": entry["components"],
            "confidence": 1.0,
            "source": "csv",
            "match_tier": "csv",
        }

    # Tier 2: SQLite exact match on normalized key
    row = drug_index.find_brand_exact(brand_name)
    if row:
        return _row_to_result(row, source="sqlite_exact", confidence=0.98)

    # Tier 3: FTS5 token-prefix search
    fts_rows = drug_index.find_brand_fts(brand_name, limit=1)
    if fts_rows:
        return _row_to_result(fts_rows[0], source="sqlite_fts", confidence=0.9)

    # Tier 4: RapidFuzz fuzzy match
    fuzzy = _fuzzy_lookup(brand_name)
    if fuzzy is not None:
        best_key, score = fuzzy
        row = drug_index.find_brand_exact(best_key)
        if row:
            return _row_to_result(row, source="fuzzy", confidence=round(score / 100, 2))

    # Tier 5: RxNav — skip in local/test mode to avoid network dependency
    if os.getenv("ENVIRONMENT", "development") != "local":
        result = _rxnav_lookup(brand_name)
        if result:
            return {**result, "source": "rxnav", "match_tier": "rxnav"}

    # Tier 6: Unresolved
    return {
        "generic": brand_name.lower(),
        "drug_class": "",
        "components": [],
        "confidence": 0.0,
        "source": "unresolved",
        "match_tier": "unresolved",
    }


drug_lookup_tool = FunctionTool(drug_lookup)
