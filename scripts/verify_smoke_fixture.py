#!/usr/bin/env python3
"""
Offline check that the 4-drug smoke fixture resolves to two dataset interactions.

Does not call Gemini — only exercises interaction_lookup via compute_prescription_safety.

Usage (from repo root):
    uv run python scripts/verify_smoke_fixture.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from tools.safety_check import compute_prescription_safety  # noqa: E402

EXPECTED_GENERICS = ["aspirin", "nimesulide", "warfarin", "metronidazole"]
EXPECTED_PAIRS = 6
EXPECTED_INTERACTIONS = 2


def main() -> None:
    result = compute_prescription_safety(EXPECTED_GENERICS, [])
    pairs = result["pairs_checked"]
    hits = result["interactions"]
    severity = result["overall_severity"]

    print(f"Generics checked : {result['current_generics']}")
    print(f"Pairs checked  : {pairs} (expected {EXPECTED_PAIRS})")
    print(f"Interactions   : {len(hits)} (expected {EXPECTED_INTERACTIONS})")
    print(f"Overall severity: {severity} (expected HIGH)")
    for item in hits:
        print(
            f"  - {item['drug_a']} + {item['drug_b']} "
            f"→ {item['severity']} ({item['source']})"
        )

    ok = (
        pairs == EXPECTED_PAIRS
        and len(hits) == EXPECTED_INTERACTIONS
        and severity == "HIGH"
    )
    if not ok:
        print("\nFAIL — ensure data/drugs.db exists (run scripts/build_drug_index.py).")
        raise SystemExit(1)
    print("\nOK — fixture matches drugs.db interactions table.")


if __name__ == "__main__":
    main()
