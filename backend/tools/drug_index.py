"""
backend/tools/drug_index.py

Shared, read-only access layer over data/drugs.db.

The SQLite file is built offline by scripts/build_drug_index.py.
This module owns the (lazy) connection and exposes typed accessor
functions used by drug_lookup, combo_splitter, and interaction_lookup.

The file is opened in read-only mode and the connection is process-wide
to avoid repeated open()s. Lookups are sub-millisecond.

If the DB is missing (e.g. fresh checkout where the artifact has not
been built yet), all accessors return empty results and emit a single
warning. Callers are expected to fall back gracefully.
"""
from __future__ import annotations

import logging
import os
import sqlite3
import threading
from pathlib import Path

from tools.data_paths import drugs_db_path
from tools.drug_normalize import canonical_pair, normalize_brand, normalize_generic

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_CONN: sqlite3.Connection | None = None
_WARNED_MISSING = False


def _download_db_from_gcs(gcs_uri: str, dest: Path) -> None:
    from google.cloud import storage

    without_scheme = gcs_uri[len("gs://") :]
    bucket_name, _, blob_name = without_scheme.partition("/")
    if not bucket_name or not blob_name:
        raise ValueError(f"Invalid DRUGS_DB_GCS_URI: {gcs_uri!r}")

    dest.parent.mkdir(parents=True, exist_ok=True)
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    bucket.blob(blob_name).download_to_filename(str(dest))
    logger.info("Downloaded drugs.db from %s to %s", gcs_uri, dest)


def _resolve_db_path() -> Path:
    local = drugs_db_path()
    if local.exists():
        return local

    gcs_uri = os.environ.get("DRUGS_DB_GCS_URI", "").strip()
    if not gcs_uri.startswith("gs://"):
        return local

    cache_dir = Path(
        os.environ.get("DRUGS_DB_CACHE_DIR", "/tmp/medication-companion-data")
    )
    cached = cache_dir / "drugs.db"
    if cached.exists():
        return cached

    try:
        _download_db_from_gcs(gcs_uri, cached)
        return cached
    except Exception as exc:
        logger.warning(
            "Failed to download drugs.db from %s: %s — drug_lookup will fall back "
            "to curated CSV only.",
            gcs_uri,
            exc,
        )
        return local


def _connect() -> sqlite3.Connection | None:
    global _CONN, _WARNED_MISSING
    if _CONN is not None:
        return _CONN
    with _LOCK:
        if _CONN is not None:
            return _CONN
        db_path = _resolve_db_path()
        if not db_path.exists():
            if not _WARNED_MISSING:
                logger.warning(
                    "drugs.db not found at %s — drug_lookup will fall back to "
                    "curated CSV only. Run scripts/build_drug_index.py or set "
                    "DRUGS_DB_GCS_URI.",
                    db_path,
                )
                _WARNED_MISSING = True
            return None
        uri = f"file:{db_path}?mode=ro"
        _CONN = sqlite3.connect(uri, uri=True, check_same_thread=False)
        _CONN.row_factory = sqlite3.Row
    return _CONN


def reset() -> None:
    """Close the cached connection (used by tests)."""
    global _CONN, _WARNED_MISSING
    with _LOCK:
        if _CONN is not None:
            _CONN.close()
            _CONN = None
        _WARNED_MISSING = False


# ── Brand lookups ────────────────────────────────────────────────────────────


def find_brand_exact(brand: str) -> dict | None:
    """Exact match on the normalized brand key. Returns the highest-priority row."""
    conn = _connect()
    if conn is None:
        return None
    key = normalize_brand(brand)
    if not key:
        return None
    cur = conn.execute(
        "SELECT brand_id, brand_norm, brand_display, manufacturer, drug_type, "
        "drug_class, source, priority FROM brands WHERE brand_norm = ? "
        "ORDER BY priority DESC LIMIT 1",
        (key,),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def find_brand_fts(brand: str, limit: int = 5) -> list[dict]:
    """
    Prefix/token search via FTS5. Used after exact-match misses.
    Builds a token-prefix query like 'azee*' so 'Azee' matches 'azee 500'.
    """
    conn = _connect()
    if conn is None:
        return []
    key = normalize_brand(brand)
    if not key:
        return []
    tokens = [t for t in key.split() if t]
    if not tokens:
        return []
    match_expr = " ".join(f"{t}*" for t in tokens)
    try:
        cur = conn.execute(
            "SELECT b.brand_id, b.brand_norm, b.brand_display, b.manufacturer, "
            "b.drug_type, b.drug_class, b.source, b.priority "
            "FROM brands_fts JOIN brands b ON b.brand_id = brands_fts.rowid "
            "WHERE brands_fts MATCH ? "
            "ORDER BY b.priority DESC, bm25(brands_fts) LIMIT ?",
            (match_expr, limit),
        )
        return [dict(r) for r in cur.fetchall()]
    except sqlite3.OperationalError as exc:
        logger.debug("FTS query failed for %r: %s", brand, exc)
        return []


def all_brand_keys() -> list[str]:
    """Return all distinct brand_norm strings (used to build a fuzzy index)."""
    conn = _connect()
    if conn is None:
        return []
    cur = conn.execute("SELECT DISTINCT brand_norm FROM brands")
    return [r[0] for r in cur.fetchall()]


# ── Components / FDC ─────────────────────────────────────────────────────────


def components_for_brand_id(brand_id: int) -> list[dict]:
    conn = _connect()
    if conn is None:
        return []
    cur = conn.execute(
        "SELECT generic_norm, dose FROM brand_components WHERE brand_id = ?",
        (brand_id,),
    )
    return [{"component": r["generic_norm"], "dose": r["dose"] or ""} for r in cur.fetchall()]


def components_for_brand_name(brand: str) -> list[dict]:
    """Convenience wrapper used by combo_splitter."""
    row = find_brand_exact(brand)
    if not row:
        return []
    return components_for_brand_id(row["brand_id"])


# ── Generic class metadata ───────────────────────────────────────────────────


def generic_meta(generic: str) -> dict | None:
    conn = _connect()
    if conn is None:
        return None
    key = normalize_generic(generic)
    if not key:
        return None
    cur = conn.execute(
        "SELECT generic_norm, display_name, therapeutic_class, chemical_class, "
        "action_class, habit_forming FROM generics WHERE generic_norm = ?",
        (key,),
    )
    row = cur.fetchone()
    return dict(row) if row else None


# ── Interactions ─────────────────────────────────────────────────────────────


def interaction(generic_a: str, generic_b: str) -> dict | None:
    conn = _connect()
    if conn is None:
        return None
    a, b = canonical_pair(generic_a, generic_b)
    if not a or not b or a == b:
        return None
    cur = conn.execute(
        "SELECT generic_a, generic_b, severity, mechanism, source "
        "FROM interactions WHERE generic_a = ? AND generic_b = ?",
        (a, b),
    )
    row = cur.fetchone()
    return dict(row) if row else None
