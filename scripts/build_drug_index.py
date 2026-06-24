#!/usr/bin/env python3
"""
scripts/build_drug_index.py

Build data/drugs.db from curated CSVs (committed) and Kaggle CSVs (download separately).

Inputs (data/):

  Curated — committed to the repo, hand-maintained:
    - india_brands.csv
        Brand → generic mappings (source='curated', highest lookup priority)
    - curated_interactions.csv
        Interaction overrides (source='curated'; wins over medicine_data on collision)

  Kaggle — not committed; download and place in data/ (see .gitignore):
    - medicine_data.csv
        Primary drug-interaction source (source='medicine_data')
        https://kaggle.com/datasets/mohneesh7/indian-medicine-data
    - Extensive_A_Z_medicines_dataset_of_India.csv
        ~250k Indian brand names (source='extensive_az')
        https://kaggle.com/datasets/riturajsingh2004/extensive-a-z-medicines-dataset-of-india
    - all_medicine databased.csv
        Fallback brand metadata (source='all_medicine')
        https://kaggle.com/datasets/ankushpoddar/all-india-drug-bank-database

Output:
  - data/drugs.db    SQLite with tables: brands, brand_components, generics,
                     interactions, plus an FTS5 index over brand keys.

Run:
  python scripts/build_drug_index.py
  python scripts/build_drug_index.py --data-dir data --out data/drugs.db
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from tools.drug_normalize import (  # noqa: E402
    canonical_pair,
    map_severity,
    normalize_brand,
    normalize_generic,
    split_components,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("build_drug_index")

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


SCHEMA_SQL = """
DROP TABLE IF EXISTS brands;
DROP TABLE IF EXISTS brand_components;
DROP TABLE IF EXISTS generics;
DROP TABLE IF EXISTS interactions;
DROP TABLE IF EXISTS brands_fts;

CREATE TABLE brands (
  brand_id        INTEGER PRIMARY KEY AUTOINCREMENT,
  brand_norm      TEXT NOT NULL,
  brand_display   TEXT NOT NULL,
  manufacturer    TEXT,
  drug_type       TEXT,
  drug_class      TEXT,
  source          TEXT NOT NULL,
  priority        INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_brands_norm ON brands(brand_norm);

CREATE TABLE brand_components (
  brand_id        INTEGER NOT NULL REFERENCES brands(brand_id),
  generic_norm    TEXT NOT NULL,
  dose            TEXT,
  PRIMARY KEY(brand_id, generic_norm)
);
CREATE INDEX idx_bc_generic ON brand_components(generic_norm);

CREATE TABLE generics (
  generic_norm        TEXT PRIMARY KEY,
  display_name        TEXT,
  therapeutic_class   TEXT,
  chemical_class      TEXT,
  action_class        TEXT,
  habit_forming       INTEGER
);

CREATE TABLE interactions (
  generic_a   TEXT NOT NULL,
  generic_b   TEXT NOT NULL,
  severity    TEXT NOT NULL CHECK(severity IN ('HIGH','MODERATE','LOW','INFO')),
  mechanism   TEXT,
  source      TEXT NOT NULL,
  PRIMARY KEY(generic_a, generic_b)
);
CREATE INDEX idx_int_a ON interactions(generic_a);
CREATE INDEX idx_int_b ON interactions(generic_b);

CREATE VIRTUAL TABLE brands_fts USING fts5(
  brand_norm,
  content='brands',
  content_rowid='brand_id',
  tokenize='unicode61'
);
"""


def open_csv(path: Path):
    """Open a CSV with utf-8-sig fallback to latin-1 to survive odd encodings."""
    try:
        return open(path, newline="", encoding="utf-8-sig")
    except UnicodeDecodeError:
        return open(path, newline="", encoding="latin-1")


# ── Source-specific row iterators ────────────────────────────────────────────


def iter_curated(path: Path):
    """data/india_brands.csv — small, hand-curated, highest precedence (priority=100)."""
    with open_csv(path) as f:
        for row in csv.DictReader(f):
            brand_display = (row.get("brand_name") or "").strip()
            if not brand_display:
                continue
            generic_raw = (row.get("generic_name") or "").strip()
            components_raw = (row.get("components") or "").strip()
            drug_class = (row.get("drug_class") or "").strip()

            if components_raw:
                comps = split_components(components_raw)
            elif generic_raw:
                comps = [(normalize_generic(generic_raw), "")] if generic_raw else []
            else:
                comps = []

            yield {
                "brand_norm": normalize_brand(brand_display),
                "brand_display": brand_display,
                "manufacturer": "",
                "drug_type": "allopathy",
                "drug_class": drug_class,
                "source": "curated",
                "priority": 100,
                "components": comps,
            }


def iter_extensive_az(path: Path):
    """data/Extensive_A_Z_medicines_dataset_of_India.csv (priority=50)."""
    with open_csv(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            brand_display = (row.get("name") or "").strip()
            if not brand_display:
                continue
            comp1 = (row.get("short_composition1") or "").strip()
            comp2 = (row.get("short_composition2") or "").strip()
            comps: list[tuple[str, str]] = []
            for raw in (comp1, comp2):
                if raw:
                    comps.extend(split_components(raw))

            yield {
                "brand_norm": normalize_brand(brand_display),
                "brand_display": brand_display,
                "manufacturer": (row.get("manufacturer_name") or "").strip(),
                "drug_type": (row.get("type") or "allopathy").strip(),
                "drug_class": (row.get("Therapeutic Class") or "").strip(),
                "source": "extensive_az",
                "priority": 50,
                "components": comps,
                "_chemical_class": (row.get("Chemical Class") or "").strip(),
                "_action_class": (row.get("Action Class") or "").strip(),
                "_habit_forming": (row.get("Habit Forming") or "").strip(),
            }


def iter_all_medicine(path: Path):
    """data/all_medicine databased.csv (priority=30, no composition column)."""
    with open_csv(path) as f:
        for row in csv.DictReader(f):
            brand_display = (row.get("name") or "").strip()
            if not brand_display:
                continue
            yield {
                "brand_norm": normalize_brand(brand_display),
                "brand_display": brand_display,
                "manufacturer": "",
                "drug_type": "allopathy",
                "drug_class": (row.get("Therapeutic Class") or "").strip(),
                "source": "all_medicine",
                "priority": 30,
                "components": [],
                "_chemical_class": (row.get("Chemical Class") or "").strip(),
                "_action_class": (row.get("Action Class") or "").strip(),
                "_habit_forming": (row.get("Habit Forming") or "").strip(),
            }


def iter_medicine_data_interactions(path: Path):
    """
    data/medicine_data.csv — emit interaction rows from the structured
    drug_interactions JSON column. salt_composition gives us the salt name.
    """
    with open_csv(path) as f:
        for row in csv.DictReader(f):
            salt_raw = (row.get("salt_composition") or "").strip()
            interactions_raw = (row.get("drug_interactions") or "").strip()
            if not salt_raw or not interactions_raw:
                continue
            salts = [g for g, _ in split_components(salt_raw)]
            if not salts:
                continue
            try:
                data = json.loads(interactions_raw)
            except json.JSONDecodeError:
                continue
            drugs = data.get("drug") or []
            effects = data.get("effect") or []
            if not isinstance(drugs, list) or not isinstance(effects, list):
                continue
            for salt_a in salts:
                for i, other_drug in enumerate(drugs):
                    if not other_drug:
                        continue
                    salt_b = normalize_generic(str(other_drug))
                    if not salt_b or salt_a == salt_b:
                        continue
                    effect = effects[i] if i < len(effects) else ""
                    severity = map_severity(effect)
                    yield (salt_a, salt_b, severity)


def iter_curated_interactions(path: Path):
    """data/curated_interactions.csv — committed smoke/regression interaction rows."""
    with open_csv(path) as f:
        for row in csv.DictReader(f):
            a = normalize_generic((row.get("generic_a") or "").strip())
            b = normalize_generic((row.get("generic_b") or "").strip())
            if not a or not b or a == b:
                continue
            severity = map_severity((row.get("severity") or "HIGH").strip())
            mechanism = (row.get("mechanism") or "").strip()
            yield (a, b, severity, mechanism)


def _load_interactions(
    data_dir: Path,
) -> dict[tuple[str, str], tuple[str, str, str]]:
    """Merge medicine_data + curated interactions; curated wins on collision."""
    sev_rank = {"HIGH": 3, "MODERATE": 2, "LOW": 1, "INFO": 0}
    best: dict[tuple[str, str], tuple[str, str, str]] = {}

    interactions_path = data_dir / "medicine_data.csv"
    if interactions_path.exists():
        logger.info("Ingesting interactions from %s …", interactions_path.name)
        for salt_a, salt_b, severity in iter_medicine_data_interactions(
            interactions_path
        ):
            key = canonical_pair(salt_a, salt_b)
            existing = best.get(key)
            if existing is None or sev_rank[severity] > sev_rank[existing[0]]:
                best[key] = (severity, "", "medicine_data")
    else:
        logger.warning("medicine_data.csv not found — skipping Kaggle interactions")

    curated_path = data_dir / "curated_interactions.csv"
    if curated_path.exists():
        logger.info("Ingesting interactions from %s …", curated_path.name)
        for a, b, severity, mechanism in iter_curated_interactions(curated_path):
            key = canonical_pair(a, b)
            best[key] = (severity, mechanism, "curated")

    return best


# ── Build pipeline ───────────────────────────────────────────────────────────


def build(data_dir: Path, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()

    conn = sqlite3.connect(str(out_path))
    conn.executescript(SCHEMA_SQL)

    sources = [
        ("curated", data_dir / "india_brands.csv", iter_curated),
        (
            "extensive_az",
            data_dir / "Extensive_A_Z_medicines_dataset_of_India.csv",
            iter_extensive_az,
        ),
        ("all_medicine", data_dir / "all_medicine databased.csv", iter_all_medicine),
    ]

    # Dedup brands: prefer the highest-priority entry for a given brand_norm.
    # Lower-priority entries with the same normalized key are skipped.
    seen_brand_norms: dict[str, int] = {}
    generic_meta: dict[str, dict] = {}
    brand_count = 0
    component_count = 0

    for source_name, path, iterator in sources:
        if not path.exists():
            logger.warning("Source %s missing: %s — skipping", source_name, path)
            continue
        logger.info("Ingesting %s …", path.name)
        rows_in = 0
        rows_kept = 0
        cur = conn.cursor()
        for row in iterator(path):
            rows_in += 1
            brand_norm = row["brand_norm"]
            if not brand_norm:
                continue
            existing_priority = seen_brand_norms.get(brand_norm)
            if existing_priority is not None and existing_priority >= row["priority"]:
                continue
            if existing_priority is not None:
                # Remove the lower-priority entry so the higher-priority one
                # can take over (keeps the table consistent).
                cur.execute("DELETE FROM brands WHERE brand_norm = ?", (brand_norm,))
                cur.execute(
                    "DELETE FROM brand_components WHERE brand_id IN "
                    "(SELECT brand_id FROM brands WHERE brand_norm = ?)",
                    (brand_norm,),
                )
            cur.execute(
                "INSERT INTO brands (brand_norm, brand_display, manufacturer, "
                "drug_type, drug_class, source, priority) VALUES (?,?,?,?,?,?,?)",
                (
                    brand_norm,
                    row["brand_display"],
                    row["manufacturer"],
                    row["drug_type"],
                    row["drug_class"],
                    row["source"],
                    row["priority"],
                ),
            )
            brand_id = cur.lastrowid
            seen_brand_norms[brand_norm] = row["priority"]
            rows_kept += 1
            brand_count += 1

            for generic_norm, dose in row["components"]:
                if not generic_norm:
                    continue
                try:
                    cur.execute(
                        "INSERT OR IGNORE INTO brand_components "
                        "(brand_id, generic_norm, dose) VALUES (?,?,?)",
                        (brand_id, generic_norm, dose),
                    )
                    component_count += cur.rowcount
                except sqlite3.IntegrityError:
                    pass

                meta = generic_meta.setdefault(
                    generic_norm,
                    {
                        "display_name": generic_norm,
                        "therapeutic_class": row.get("drug_class") or "",
                        "chemical_class": row.get("_chemical_class") or "",
                        "action_class": row.get("_action_class") or "",
                        "habit_forming": row.get("_habit_forming") or "",
                    },
                )
                # Fill blanks if a later source provides better metadata.
                if not meta["therapeutic_class"] and row.get("drug_class"):
                    meta["therapeutic_class"] = row["drug_class"]
                if not meta["chemical_class"] and row.get("_chemical_class"):
                    meta["chemical_class"] = row["_chemical_class"]
                if not meta["action_class"] and row.get("_action_class"):
                    meta["action_class"] = row["_action_class"]
                if not meta["habit_forming"] and row.get("_habit_forming"):
                    meta["habit_forming"] = row["_habit_forming"]

            if rows_in % 50000 == 0:
                conn.commit()
                logger.info("  %s rows read, %s brands kept …", rows_in, rows_kept)
        conn.commit()
        logger.info("  %s: %s rows read, %s brands kept", source_name, rows_in, rows_kept)

    # Generics table
    cur = conn.cursor()
    for gn, meta in generic_meta.items():
        habit = meta["habit_forming"].strip().lower()
        habit_int = 1 if habit in ("yes", "y", "true", "1") else 0
        cur.execute(
            "INSERT OR REPLACE INTO generics "
            "(generic_norm, display_name, therapeutic_class, chemical_class, "
            "action_class, habit_forming) VALUES (?,?,?,?,?,?)",
            (
                gn,
                meta["display_name"],
                meta["therapeutic_class"],
                meta["chemical_class"],
                meta["action_class"],
                habit_int,
            ),
        )
    conn.commit()
    logger.info("Generics indexed: %s", len(generic_meta))

    # Interactions (medicine_data.csv + curated_interactions.csv)
    best = _load_interactions(data_dir)
    interaction_count = 0
    cur = conn.cursor()
    for (a, b), (severity, mechanism, source) in best.items():
        cur.execute(
            "INSERT OR REPLACE INTO interactions "
            "(generic_a, generic_b, severity, mechanism, source) VALUES (?,?,?,?,?)",
            (a, b, severity, mechanism, source),
        )
        interaction_count += 1
    conn.commit()

    # Rebuild FTS index from final brands content
    logger.info("Building FTS index …")
    cur = conn.cursor()
    cur.execute("INSERT INTO brands_fts(brands_fts) VALUES ('rebuild')")
    conn.commit()

    # Stats
    logger.info("=" * 60)
    logger.info("Brands:       %s", brand_count)
    logger.info("Components:   %s", component_count)
    logger.info("Generics:     %s", len(generic_meta))
    logger.info("Interactions: %s", interaction_count)
    logger.info("Output:       %s (%.1f MB)", out_path, out_path.stat().st_size / 1e6)

    conn.execute("VACUUM")
    conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default=str(REPO_ROOT / "data"))
    parser.add_argument("--out", default=str(REPO_ROOT / "data" / "drugs.db"))
    args = parser.parse_args()

    build(Path(args.data_dir).resolve(), Path(args.out).resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
