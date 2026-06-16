"""
backend/tools/combo_splitter.py
FunctionTool: split fixed-dose combination (FDC) drugs into components.

Reads the 'components' column of data/india_brands.csv. Components are
pipe-separated strings like "pantoprazole 40mg|domperidone 10mg".
Returns an empty list for drugs that are not FDCs.
"""
import csv
import logging
from pathlib import Path

from google.adk.tools import FunctionTool

logger = logging.getLogger(__name__)

_CSV_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "india_brands.csv"

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
            dose = tokens[-1]
            component = " ".join(tokens[:-1])
        else:
            component = part
            dose = ""
        parts.append({"component": component, "dose": dose})
    return parts


def _load_combos() -> dict[str, list[dict]]:
    combos: dict[str, list[dict]] = {}
    try:
        with open(_CSV_PATH, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                raw = row.get("components", "").strip()
                if not raw:
                    continue
                parts = _parse_components(raw)
                if not parts:
                    continue
                brand_key = row["brand_name"].strip().lower()
                generic_key = row["generic_name"].strip().lower()
                combos[brand_key] = parts
                combos[generic_key] = parts
    except FileNotFoundError:
        logger.warning(
            "india_brands.csv not found — combo_splitter will return empty lists"
        )
    return combos


def _combos() -> dict[str, list[dict]]:
    global _COMBO_MAP
    if _COMBO_MAP is None:
        _COMBO_MAP = _load_combos()
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
    return _combos().get(drug_name.strip().lower(), [])


combo_splitter_tool = FunctionTool(combo_splitter)
