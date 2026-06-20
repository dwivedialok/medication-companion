"""
backend/tools/interaction_lookup.py
FunctionTool: deterministic drug-drug interaction lookup.

Backed by the interactions table in data/drugs.db (built by
scripts/build_drug_index.py from the Indian medicine dataset).

Severity vocabulary is constrained to the project hard-rule values:
  HIGH | MODERATE | LOW | INFO | NONE

When the pair is not in the table, returns severity='NONE' and
source='none'. Agent 3 may still emit an INFO finding using
pharmacological reasoning in that case (see agent3_safety.py).
"""
from __future__ import annotations

import logging

from google.adk.tools import FunctionTool

from tools import drug_index
from tools.drug_normalize import normalize_generic

logger = logging.getLogger(__name__)


def interaction_lookup(generic_a: str, generic_b: str) -> dict:
    """
    Look up a known drug-drug interaction between two generic drug names.

    Args:
        generic_a: First generic name (e.g. "warfarin", "aspirin").
        generic_b: Second generic name.

    Returns:
        dict with keys:
          severity (str)   -- "HIGH" | "MODERATE" | "LOW" | "INFO" | "NONE"
          mechanism (str)  -- brief plain-language mechanism (may be "")
          source (str)     -- "dataset" if found, "none" otherwise
          generic_a (str)  -- canonicalized (normalized + sorted) generic
          generic_b (str)  -- canonicalized counterpart
    """
    a_norm = normalize_generic(generic_a)
    b_norm = normalize_generic(generic_b)
    if not a_norm or not b_norm or a_norm == b_norm:
        return {
            "severity": "NONE",
            "mechanism": "",
            "source": "none",
            "generic_a": a_norm,
            "generic_b": b_norm,
        }

    row = drug_index.interaction(a_norm, b_norm)
    if row:
        return {
            "severity": row["severity"],
            "mechanism": row.get("mechanism") or "",
            "source": "dataset",
            "generic_a": row["generic_a"],
            "generic_b": row["generic_b"],
        }

    a_sorted, b_sorted = sorted([a_norm, b_norm])
    return {
        "severity": "NONE",
        "mechanism": "",
        "source": "none",
        "generic_a": a_sorted,
        "generic_b": b_sorted,
    }


interaction_lookup_tool = FunctionTool(interaction_lookup)
