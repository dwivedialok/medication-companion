"""
backend/evaluation/drug_lookup_eval.py

Offline evaluation harness for backend/tools/drug_lookup.py.

Builds three test sets:
  1. POSITIVE: all rows from the curated data/india_brands.csv — every entry
     must resolve to the labelled generic (top-1 precision = 1.0).
  2. OCR_NOISE: hand-crafted brand strings simulating OCR errors (digit/letter
     confusion, missing spaces, single-char substitutions). Must resolve to the
     correct generic; allowed to use any tier.
  3. NEGATIVE: synthetic non-drug strings. Must return source='unresolved'.

Reports overall precision/recall/UNRESOLVED-rate plus a per-tier hit
distribution. Used by tests/test_drug_lookup_eval.py as a CI gate, and
runnable as a script for ad-hoc inspection.
"""
from __future__ import annotations

import csv
import os
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault("ENVIRONMENT", "local")
os.environ.setdefault("MEMORY_BACKEND", "local")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

CURATED_CSV = REPO_ROOT / "data" / "india_brands.csv"


# Hand-crafted OCR-style noise pairs: (noisy_input, expected_generic_substring).
OCR_NOISE_CASES: list[tuple[str, str]] = [
    ("Azee5O0", "azithromycin"),
    ("Azee 5OO", "azithromycin"),
    ("Pantocld", "pantoprazole"),
    ("Augmcntin", "amoxicillin"),
    ("D0lo 650", "paracetamol"),
    ("Combiflarn", "ibuprofen"),
    ("Ecospnn", "aspirin"),
    ("Glycomet 5O0", "metformin"),
    ("Telma  AM", "telmisartan"),
    ("PANTOCID  DSR", "pantoprazole"),
]


NEGATIVE_CASES: list[str] = [
    "CompletelyUnknownXYZ9999",
    "asdfqwerty",
    "lorem ipsum dolor",
    "12345",
    "the quick brown fox",
]


@dataclass
class EvalReport:
    positive_total: int
    positive_hits: int
    ocr_total: int
    ocr_hits: int
    negative_total: int
    negative_correct: int
    tier_counts: Counter
    failures: list[tuple[str, str, str]]  # (input, expected, got)

    @property
    def positive_precision(self) -> float:
        return self.positive_hits / self.positive_total if self.positive_total else 0.0

    @property
    def ocr_recall(self) -> float:
        return self.ocr_hits / self.ocr_total if self.ocr_total else 0.0

    @property
    def negative_specificity(self) -> float:
        return (
            self.negative_correct / self.negative_total if self.negative_total else 0.0
        )

    def summary(self) -> str:
        lines = [
            "Drug-lookup evaluation",
            "=" * 60,
            f"Positive (curated):  {self.positive_hits}/{self.positive_total} "
            f"({self.positive_precision:.1%})",
            f"OCR-noise recall:    {self.ocr_hits}/{self.ocr_total} "
            f"({self.ocr_recall:.1%})",
            f"Negative specificity:{self.negative_correct}/{self.negative_total} "
            f"({self.negative_specificity:.1%})",
            "",
            "Tier distribution:",
        ]
        for tier, count in self.tier_counts.most_common():
            lines.append(f"  {tier:<16} {count}")
        if self.failures:
            lines.append("")
            lines.append(f"Failures ({len(self.failures)}):")
            for inp, exp, got in self.failures[:20]:
                lines.append(f"  {inp!r:<30}  expected={exp!r}  got={got!r}")
            if len(self.failures) > 20:
                lines.append(f"  … {len(self.failures) - 20} more")
        return "\n".join(lines)


def _load_curated() -> list[tuple[str, str]]:
    """Return [(brand, expected_generic_substring), ...]."""
    out: list[tuple[str, str]] = []
    if not CURATED_CSV.exists():
        return out
    with open(CURATED_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            brand = (row.get("brand_name") or "").strip()
            generic = (row.get("generic_name") or "").strip().lower()
            if not brand or not generic:
                continue
            primary = generic.split("+")[0].strip()
            out.append((brand, primary))
    return out


def run_eval() -> EvalReport:
    from tools.drug_lookup import drug_lookup

    tier_counts: Counter = Counter()
    failures: list[tuple[str, str, str]] = []

    positive_total = 0
    positive_hits = 0
    for brand, expected in _load_curated():
        positive_total += 1
        result = drug_lookup(brand)
        tier_counts[result["match_tier"]] += 1
        if expected in result["generic"]:
            positive_hits += 1
        else:
            failures.append((brand, expected, result["generic"]))

    ocr_total = 0
    ocr_hits = 0
    for noisy, expected in OCR_NOISE_CASES:
        ocr_total += 1
        result = drug_lookup(noisy)
        tier_counts[result["match_tier"]] += 1
        if expected in result["generic"]:
            ocr_hits += 1
        else:
            failures.append((noisy, expected, result["generic"]))

    negative_total = 0
    negative_correct = 0
    for inp in NEGATIVE_CASES:
        negative_total += 1
        result = drug_lookup(inp)
        tier_counts[result["match_tier"]] += 1
        if result["source"] == "unresolved":
            negative_correct += 1
        else:
            failures.append((inp, "unresolved", result["source"]))

    return EvalReport(
        positive_total=positive_total,
        positive_hits=positive_hits,
        ocr_total=ocr_total,
        ocr_hits=ocr_hits,
        negative_total=negative_total,
        negative_correct=negative_correct,
        tier_counts=tier_counts,
        failures=failures,
    )


if __name__ == "__main__":
    report = run_eval()
    print(report.summary())
