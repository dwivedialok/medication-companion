"""
backend/tools/combo_splitter.py
FunctionTool: split fixed-dose combination (FDC) drugs into components.

Backed by data/drugs.db (built by scripts/build_drug_index.py). For brands
that exist in the curated data/india_brands.csv but are missing from the
DB build (fresh checkout), we fall back to parsing india_brands.csv directly.
"""
from __future__ import annotations

import csv
import logging

from google.adk.tools import FunctionTool

from tools import drug_index
from tools.data_paths import india_brands_csv
from tools.drug_normalize import normalize_brand

logger = logging.getLogger(__name__)

# Public cache symbol preserved for backward compatibility with existing tests
# (tests reset `tools.combo_splitter._COMBO_MAP = None`).
_COMBO_MAP: dict[str, list[dict]] | None = None


def _parse_components(raw: str) -> list[dict]:
    """Parse "drug 40mg|drug2 10mg" into [{component, dose}, ...]."""
    parts = []
    for part in raw.split("|"):
        part = part.strip()
        if not part:
            continue
        tokens = part.split()
        if len(tokens) >= 2:
            parts.append({"component": " ".join(tokens[:-1]), "dose": tokens[-1]})
        else:
            parts.append({"component": part, "dose": ""})
    return parts


def _load_combos_from_csv() -> dict[str, list[dict]]:
    """Fallback combo map sourced from the curated CSV only."""
    combos: dict[str, list[dict]] = {}
    try:
        with open(india_brands_csv(), newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                raw = (row.get("components") or "").strip()
                if not raw:
                    continue
                parts = _parse_components(raw)
                if not parts:
                    continue
                brand_key = normalize_brand(row.get("brand_name") or "")
                generic_key = normalize_brand(row.get("generic_name") or "")
                if brand_key:
                    combos[brand_key] = parts
                if generic_key:
                    combos.setdefault(generic_key, parts)
    except FileNotFoundError:
        logger.warning(
            "india_brands.csv not found — combo_splitter falling back to DB only"
        )
    return combos


def _combos() -> dict[str, list[dict]]:
    global _COMBO_MAP
    if _COMBO_MAP is None:
        _COMBO_MAP = _load_combos_from_csv()
    return _COMBO_MAP


def combo_splitter(drug_name: str) -> list[dict]:
    """
    Split a fixed-dose combination (FDC) drug into its active components.

    Args:
        drug_name: Brand or generic name of the drug
                   (e.g. "Pantocid DSR", "Combiflam", "Cheston Cold").

    Returns:
        List of {"component": str, "dose": str} dicts.
        Empty list if the drug is not a known FDC.
    """
    key = normalize_brand(drug_name)
    if not key:
        return []

    csv_hit = _combos().get(key)
    if csv_hit:
        return csv_hit

    db_components = drug_index.components_for_brand_name(drug_name)
    if len(db_components) >= 2:
        return db_components

    return []


combo_splitter_tool = FunctionTool(combo_splitter)
