# Skill: Add a new drug data source

Reusable workflow for extending the drug lookup index. Follow after updating
[AGENTS.md](../../AGENTS.md) if lookup behaviour changes.

## When to use

- Adding a new CSV or external dataset for brand→generic mapping
- Adding interaction rows to `data/drugs.db`
- Fixing systematic UNRESOLVED results for known Indian brands

## Prerequisites

- Python 3.11+ with repo dependencies (`uv sync`)
- New CSV placed under `data/` (Kaggle CSVs stay gitignored except `india_brands.csv`)

## Steps

1. **Choose priority tier** — read lookup order in [backend/tools/drug_lookup.py](../../backend/tools/drug_lookup.py):
   - Curated CSV (`india_brands.csv`) = highest priority
   - SQLite exact / FTS / fuzzy = built index
   - RxNav = production only (`ENVIRONMENT != local`)

2. **Extend the build script** — edit [scripts/build_drug_index.py](../../scripts/build_drug_index.py):
   - Add an iterator function for the new source (do not hard-code paths in tool files)
   - Map columns to: `brand_norm`, `generic`, `source`, optional `therapeutic_class`
   - For interactions: emit rows into the `interactions` table schema (see [specs/schemas/interaction_matrix.yaml](../../specs/schemas/interaction_matrix.yaml))

3. **Rebuild the index**

   ```bash
   uv run python scripts/build_drug_index.py
   ```

   Output: `data/drugs.db` (~60 MB, committed).

4. **Add eval cases** — extend [tests/unit/test_drug_lookup_eval.py](../../tests/unit/test_drug_lookup_eval.py):
   - At least one positive match from the new source
   - One OCR-noise variant if brands are handwritten on prescriptions
   - One negative case (must stay UNRESOLVED, not hallucinate)

5. **Run tests**

   ```bash
   uv run pytest tests/unit/test_drug_lookup.py tests/unit/test_drug_lookup_eval.py tests/unit/test_interaction_lookup.py
   ```

6. **Update docs** — note the new source in AGENTS.md "Drug data sources" if it is a permanent tier.

## Do not

- Hard-code CSV paths inside `backend/tools/drug_lookup.py`
- Commit raw Kaggle CSVs (only `india_brands.csv` and rebuilt `drugs.db`)
- Add new severity levels beyond `HIGH | MODERATE | LOW | INFO | NONE`
