# AGENTS.md

> This file follows the 2026 Kaggle AI Agents Intensive convention.
> It is the primary context file for coding agents (Cursor, Claude Code, Jules, etc.)
> working in this repository. Update it every time agent behaviour changes.

---

## Project overview

**Medication Companion** is a multi-agent AI system (Google ADK + Gemini) that helps patients in India
understand prescriptions and flag drug interactions across multiple visits.

**Stack:** Python 3.11 · Google ADK · FastAPI · Flutter · GCP (Cloud Run, Vertex AI, Firebase)

---

## Hard rules (non-negotiable)

1. Never generate diagnostic language ("you have", "this indicates a condition")
2. Every patient-facing string ends with "Please discuss this with your doctor or pharmacist."
3. Never store prescription images or clinical notes in memory — only resolved generic drug names
4. Never call raw Gemini API — always use `google.adk LlmAgent`
5. Never use `print()` in production paths — use `google.cloud.logging`
6. Never deploy backend services with `--allow-unauthenticated` except the **auth broker** when fronted by Firebase Hosting rewrites (Google requires public Cloud Run invoke; `/upload-url` and `/prescription` still verify Firebase JWT). Agent Runtime stays private.
7. `patient_id` comes from verified Firebase JWT — never from client body

---

## Workflow

```
backend/agents/    → agent logic (each agent is one file, one responsibility)
backend/tools/     → FunctionTools (one tool per file, fully typed, testable in isolation)
backend/memory/    → session + memory wrappers
backend/evaluation/→ LLM-as-Judge (async, non-blocking) + tool eval harnesses
frontend/lib/      → Flutter app
data/              → curated CSV (committed) + drugs.db SQLite index (committed)
deploy/            → deployment scripts
                   → auth_broker/ (Cloud Run token broker)
                   → legacy_cloud_run/ (archived FastAPI + A2A)
scripts/           → GCP setup/teardown + drug index builder
```

## Drug data sources

The drug lookup pipeline is backed by `data/drugs.db`, an SQLite index built
from three sources:

- `data/india_brands.csv` (curated, ~300 rows, hand-maintained, highest priority)
- `data/Extensive_A_Z_medicines_dataset_of_India.csv` (Kaggle, ~250k brands)
- `data/all_medicine databased.csv` (Kaggle, fallback brand metadata)
- `data/medicine_data.csv` (Kaggle, primary drug-interaction source)

The Kaggle CSVs are NOT committed (see `.gitignore`). Drop them into `data/`
and run:

```bash
python scripts/build_drug_index.py
```

This rebuilds `data/drugs.db` (~60 MB, committed). The build must be re-run
whenever a CSV is updated or a new source is added.

Lookup tiers in `backend/tools/drug_lookup.py` (first hit wins):
1. curated CSV exact match (`source=csv`, confidence=1.0)
2. SQLite exact match on normalized brand key (`sqlite_exact`)
3. SQLite FTS5 prefix search (`sqlite_fts`)
4. RapidFuzz Levenshtein fuzzy match with OCR-confusion folding (`fuzzy`)
5. RxNav REST API (skipped when `ENVIRONMENT=local`)
6. UNRESOLVED

Agent 3 (safety) calls `interaction_lookup(generic_a, generic_b)` on every
drug pair. The tool returns severity from the `interactions` table when
present; otherwise the LLM may fall back to pharmacological reasoning and
emit `INFO`.

Quality is gated by `backend/tests/test_drug_lookup_eval.py`, which exercises
the curated set, hand-crafted OCR-noise inputs, and negative cases.

## Agent Runtime + auth broker

- **Agent Runtime** hosts the ADK pipeline (`backend/agent_runtime_app.py`).
  Deploy with `agents-cli deploy`; do not expose it directly to clients.
- **Auth broker** (`backend/auth_broker/`) is the only client-facing HTTP API.
  It verifies Firebase JWTs, issues GCS signed upload URLs, and proxies to
  Agent Runtime using service-account credentials.
- `patient_id` is always derived from the verified Firebase UID in the broker.
- Image transport: client uploads to GCS via signed URL, then sends `gs://` URI
  to `/prescription`. Agent 1 reads the image via `Part.from_uri`.
- Local dev: `make local-auth-broker` (HTTP token broker on :8080). Set
  `USE_LOCAL_RUNNER=true` to run the pipeline in-process without a deployed
  Agent Runtime (broker still uses real GCS for uploads).
- Pub/Sub ambient-agent wiring (Day 4 follow-up) is a separate concern — do not
 conflate it with this HTTP auth broker.
- Operational deploy commands (Agent Runtime, auth broker, Firebase Hosting,
 incremental updates) live in [`docs/deployment_runbook.md`](docs/deployment_runbook.md).

---

## Instruction hierarchy (Day 5)

Layered instructions — check the most specific layer first:

| Layer | Location | Purpose |
|-------|----------|---------|
| Chat | Cursor / Jules session | Short-lived task orchestration |
| Specs | [`specs/`](specs/) | Gherkin scenarios + flat YAML schemas (source of truth) |
| Agent skills | [`.agent/skills/`](.agent/skills/) | Reusable feature workflows |
| Model overrides | [`backend/agents/GEMINI.md`](backend/agents/GEMINI.md) | Per-agent Gemini config |
| Global DNA | This file + [`.cursor/rules/medication-companion.mdc`](.cursor/rules/medication-companion.mdc) | Hard rules |

For evidence-driven debugging, use templates in [`docs/forensic_prompts.md`](docs/forensic_prompts.md).

---

## Adding a new feature

1. Update this file first with the new rule or boundary
2. Update `specs/` (scenario or schema) if behaviour changes
3. Update `.cursor/rules/medication-companion.mdc` if it affects agent/tool behaviour
4. Write the test in `tests/unit/` or `tests/integration/` before generating the implementation
5. Implement in the appropriate `agents/` or `tools/` file
6. Run `uv run pytest tests/unit tests/integration` — all tests must pass before committing
7. For production incidents, start from [`docs/forensic_prompts.md`](docs/forensic_prompts.md)

---

## Environment setup

```bash
cd backend
cp ../.env.example .env.local
# Set MEMORY_BACKEND=local for development (no GCP credentials needed)
pip install -r requirements.txt
pytest tests/
```

---

## What not to do

- Do not add a new agent without updating the agent boundary table in `.cursor/rules/`
- Do not add a tool that calls another agent — tools are leaf nodes
- Do not add GCP credentials to `.env.example` — that file is committed
- Do not add new severity levels — only: `HIGH`, `MODERATE`, `LOW`, `INFO`, `NONE`
- Do not add a new drug data source by hard-coding paths in tool files —
  add the source iterator to `scripts/build_drug_index.py` and rebuild `data/drugs.db`
- Do not check raw Kaggle CSVs into git — only the curated `india_brands.csv`
  and the built `drugs.db` are committed

---

## Known follow-ups (post-capstone)

Full product backlog: [`docs/BACKLOG.md`](docs/BACKLOG.md).

- **Bind GCS upload URI to authenticated patient.** `/prescription` must not
  accept a `gcs_uri` issued to a different Firebase UID. Required before public
  launch; not capstone-blocking. See BACKLOG for options.
- **Migrate `SequentialAgent` → `Workflow` (graph DAG).** `google-adk` 2.3.0
  deprecates `SequentialAgent`; the new graph-based `Workflow` API (`Node`,
  `Edge`, `JoinNode`, `START`) is the long-term replacement but is a real
  refactor — callback model differs and the Agent Runtime `AdkApp` wrapper
  must be re-validated. Deprecation warning is filtered in `pyproject.toml`
  until then.
