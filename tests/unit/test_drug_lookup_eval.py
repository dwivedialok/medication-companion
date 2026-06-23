"""
Evaluation gate for backend/tools/drug_lookup.py.

Asserts minimum quality thresholds on curated, OCR-noise, and negative
test sets. Treat as a regression check: if tier weights, thresholds, or
the data pipeline change, run scripts/build_drug_index.py and re-tune.
"""
import os

import pytest

os.environ.setdefault("ENVIRONMENT", "local")
os.environ.setdefault("MEMORY_BACKEND", "local")


@pytest.fixture(autouse=True)
def _reset_caches():
    import tools.drug_lookup as dl
    from tools import drug_index
    dl._INDIA_BRANDS = None
    dl._FUZZY_KEYS = None
    drug_index.reset()
    yield
    dl._INDIA_BRANDS = None
    dl._FUZZY_KEYS = None
    drug_index.reset()


def _run():
    from evaluation.drug_lookup_eval import run_eval
    return run_eval()


def test_positive_precision_at_least_99_percent():
    report = _run()
    assert report.positive_precision >= 0.99, report.summary()


def test_ocr_recall_at_least_90_percent():
    report = _run()
    assert report.ocr_recall >= 0.9, report.summary()


def test_negative_specificity_100_percent():
    report = _run()
    assert report.negative_specificity == 1.0, report.summary()


def test_tier_distribution_uses_csv_and_fuzzy():
    """Sanity check: tier mix should include csv (positives) and fuzzy (OCR)."""
    report = _run()
    assert report.tier_counts["csv"] > 100, report.summary()
    assert report.tier_counts.get("fuzzy", 0) >= 5, report.summary()
