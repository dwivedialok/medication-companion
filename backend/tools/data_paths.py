"""
backend/tools/data_paths.py

Resolve committed data artifacts for local dev and Agent Runtime deploys.

Local dev: repo-root data/ (data/drugs.db, data/india_brands.csv).
Agent Runtime: only backend/ is packaged — deploy copies india_brands.csv into
backend/data/; drugs.db is fetched from GCS via DRUGS_DB_GCS_URI at runtime.
"""
from __future__ import annotations

from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    """Prefer backend/data (deploy bundle), else repo-root data/."""
    bundled = _BACKEND_DIR / "data"
    if bundled.is_dir():
        return bundled
    return _BACKEND_DIR.parent / "data"


def india_brands_csv() -> Path:
    return data_dir() / "india_brands.csv"


def drugs_db_path() -> Path:
    return data_dir() / "drugs.db"
