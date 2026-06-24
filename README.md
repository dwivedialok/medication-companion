# 💊 Medication Companion

> A multi-agent AI system that helps patients in India understand their prescriptions
> and stay safe across multiple visits and multiple doctors.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Flutter](https://img.shields.io/badge/Flutter-3.x-02569B?logo=flutter)](https://flutter.dev)
[![Google ADK](https://img.shields.io/badge/Google%20ADK-2.x-4285F4)](https://google.github.io/adk-docs/)
[![Gemini](https://img.shields.io/badge/Gemini-3.1%20Flash%20Lite-1a73e8)](https://ai.google.dev/)
[![GCP](https://img.shields.io/badge/GCP-Cloud%20Run%20%2B%20Vertex%20AI-orange)](https://cloud.google.com/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

---

## Table of contents

- [What it does](#what-it-does)
- [Architecture](#architecture)
- [Repository layout](#repository-layout)
- [Quick start](#quick-start-local-development)
- [Drug data sources](#drug-data-sources)
- [Deployment](#deployment)
- [Specs and instruction hierarchy](#specs-and-instruction-hierarchy)
- [Key design decisions](#key-design-decisions)
- [Out of scope](#out-of-scope)
- [Contributing](#contributing)
- [Security](#security)
- [Acknowledgements](#acknowledgements)
- [Disclaimer](#disclaimer)
- [License](#license)

---

## What it does

A patient photographs their prescription. The system runs a five-agent pipeline:

1. **Reads** the image — extracts drug names with Gemini Vision (`prescription_reader`)
2. **Resolves** brand → generic names and splits fixed-dose combinations (`medication_resolver`)
3. **Checks safety** — flags interactions against the patient's current *and* past medications via cross-visit memory (`reconciliation_safety`)
4. **Explains** the findings in plain, severity-calibrated language (`patient_education`)
5. **Localises** the explanation into the patient's preferred language and synthesises audio (`localisation_audio`)

> ⚠️ **This is not a medical device.** Every output directs the patient back to their doctor or pharmacist. It is an educational prototype, not a substitute for professional medical advice.

---

## Architecture

![Medication Companion — system architecture](docs/architecture.png)

**GCP services used:** Cloud Run · Vertex AI Agent Engine · Vertex AI Memory Bank · Cloud Storage · Cloud Text-to-Speech · Pub/Sub · BigQuery · Firebase Auth · Firebase Hosting · Cloud Trace · Cloud Logging.

Agent-level pipeline flow, session state, memory, and security details are in [`docs/architecture.md`](docs/architecture.md). Operational deploy steps are in [`docs/deployment_runbook.md`](docs/deployment_runbook.md).

---

## Repository layout

```
medication-companion/
├── backend/                          # Python — ADK agents, tools, runtime
│   ├── agents/                       # One agent per file
│   │   ├── agent1_reader.py          # Prescription Reader (Gemini Vision)
│   │   ├── agent2_resolver.py       # Medication Resolver (SQLite + RxNav)
│   │   ├── agent3_safety.py         # Reconciliation + Safety
│   │   ├── agent4_education.py      # Patient Education
│   │   ├── agent5_localisation.py   # Localisation + TTS audio
│   │   └── GEMINI.md                 # Per-agent model selection / overrides
│   ├── tools/                        # FunctionTools (leaf nodes, fully typed)
│   │   ├── drug_lookup.py            # Brand → generic (CSV → SQLite → RxNav)
│   │   ├── interaction_lookup.py     # Severity from interactions table
│   │   ├── combo_splitter.py         # Fixed-dose combination splitter
│   │   ├── safety_check.py           # Pair-wise interaction scan
│   │   ├── patient_memory.py         # Memory Bank read/write
│   │   ├── tts.py                    # Cloud Text-to-Speech
│   │   └── guardrails.py             # Input/output safety callbacks
│   ├── memory/                       # Session + Memory Bank wrappers
│   ├── evaluation/                   # LLM-as-Judge scorer (async → BigQuery)
│   ├── auth_broker/                  # Public HTTP API (Firebase JWT)
│   ├── workers/                      # Pub/Sub push worker (async path)
│   ├── policy/                       # Output policy gates
│   ├── agent_runtime_app.py          # Vertex AI Agent Runtime entry point
│   ├── agent.py                      # SequentialAgent assembly
│   └── tests/                        # pytest unit + integration suites
├── frontend/                         # Flutter PWA
│   ├── lib/
│   │   ├── auth/                     # Firebase Auth
│   │   ├── screens/                  # Login, Upload, Result
│   │   ├── services/                 # API client (attaches Firebase JWT)
│   │   ├── l10n/                     # ARB files (en, hi, bn, ta, te)
│   │   └── models/                   # Pipeline result models
│   └── pubspec.yaml
├── specs/                            # Source-of-truth behavioural specs
│   ├── pipeline.feature              # Gherkin scenarios
│   ├── safety_refusal.feature
│   ├── agent_boundaries.yaml         # Per-agent I/O + forbidden actions
│   └── schemas/                      # Flat YAML schemas
├── data/
│   ├── india_brands.csv              # Curated brand → generic (committed)
│   ├── curated_interactions.csv      # Curated interaction overrides (committed)
│   ├── drugs.db                      # Built SQLite index (committed, ~60 MB)
│   └── *.csv                         # Kaggle sources — download separately (see below)
├── scripts/                          # Build, setup, ops helpers
│   ├── build_drug_index.py           # Rebuild drugs.db from sources
│   ├── setup_gcp.sh                  # One-time GCP project setup
│   └── teardown_gcp.sh
├── deploy/
│   ├── auth_broker/                  # Auth-broker Cloud Run image
│   ├── workers/                      # Pub/Sub worker Cloud Run image
│   └── deploy.sh
├── notebooks/
│   └── medication_companion_demo.ipynb   # End-to-end demo notebook
├── docs/                             # Architecture, runbook, backlog, etc.
├── .agent/skills/                    # Reusable agent-workflow skills
├── .github/workflows/                # CI + deploy pipelines
├── AGENTS.md                         # Project DNA for coding agents
├── Makefile
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── SECURITY.md
├── LICENSE
└── README.md
```

---

## Quick start (local development)

### Prerequisites

- Python 3.11+ (project uses `uv` for dependency management)
- Flutter 3.x (only required for frontend work)
- Google Cloud SDK (`gcloud`) — only required for deploys
- A GCP project with billing enabled — only required for Vertex AI / Memory Bank

### 1. Run the agent pipeline in-process

No GCP credentials required. Uses `InMemorySessionService` and the committed
SQLite drug index.

```bash
cd backend
cp ../.env.example .env.local         # set MEMORY_BACKEND=local
uv sync
uv run pytest tests/unit tests/integration
```

### 2. Run the auth broker + local pipeline

Runs the HTTP auth broker against a local in-process pipeline (`USE_LOCAL_RUNNER=true`),
with real GCS for image uploads.

```bash
make local-auth-broker      # http://localhost:8080
```

### 3. Try the demo notebook

```bash
jupyter notebook notebooks/medication_companion_demo.ipynb
```

The notebook runs all five agents end-to-end with no GCP credentials required.

### 4. Build the drug index (optional)

Only needed if you change a source CSV or want to rebuild from the Kaggle
datasets. The committed `data/drugs.db` is sufficient for development.

```bash
python scripts/build_drug_index.py
```

See [Drug data sources](#drug-data-sources) for download links and
[`AGENTS.md`](AGENTS.md#drug-data-sources) for the lookup-tier contract.

---

## Drug data sources

`data/drugs.db` is built by [`scripts/build_drug_index.py`](scripts/build_drug_index.py)
from curated CSVs (committed) plus three Kaggle datasets (not committed).
Drop the Kaggle CSVs into `data/` and run the build script to regenerate the index.

### Curated (committed)

| File | Purpose |
|------|---------|
| [`data/india_brands.csv`](data/india_brands.csv) | Hand-maintained brand → generic mappings (~300 rows; highest lookup priority) |
| [`data/curated_interactions.csv`](data/curated_interactions.csv) | Hand-maintained interaction overrides (wins over Kaggle data on collision) |

### Kaggle (download required)

| Save as | Dataset | Role |
|---------|---------|------|
| `medicine_data.csv` | [Indian Medicine Data](https://kaggle.com/datasets/mohneesh7/indian-medicine-data) | Primary drug-interaction source |
| `Extensive_A_Z_medicines_dataset_of_India.csv` | [Extensive A–Z Medicines Dataset of India](https://kaggle.com/datasets/riturajsingh2004/extensive-a-z-medicines-dataset-of-india) | ~250k Indian brand names |
| `all_medicine databased.csv` | [All India Drug Bank Database](https://kaggle.com/datasets/ankushpoddar/all-india-drug-bank-database) | Fallback brand metadata |

The committed `data/drugs.db` (~60 MB) is enough for local development without
downloading the Kaggle CSVs.

---

## Deployment

Full operational instructions — including IAM, secrets, incremental updates,
and rollback — live in [`docs/deployment_runbook.md`](docs/deployment_runbook.md).

The high-level flow:

```bash
gcloud config set project YOUR_PROJECT_ID

./scripts/setup_gcp.sh             # one-time: APIs, GCS, Pub/Sub, IAM
make deploy-backend                # Agent Runtime + auth broker + worker
make deploy-frontend               # Flutter web → Firebase Hosting
```

> **Security:** only the auth broker is publicly invokable. Agent Runtime and
> the Pub/Sub worker stay private and are reached via service-account
> credentials. `patient_id` is always derived from the verified Firebase JWT.

---

## Specs and instruction hierarchy

The project follows a layered, spec-driven workflow. Layers are checked from
most-specific to least-specific:

| Layer | Location | Purpose |
|-------|----------|---------|
| Chat | Current coding-agent session | Short-lived task orchestration |
| Specs | [`specs/`](specs/) | Gherkin scenarios + flat YAML schemas (source of truth) |
| Agent skills | [`.agent/skills/`](.agent/skills/) | Reusable feature workflows |
| Model overrides | [`backend/agents/GEMINI.md`](backend/agents/GEMINI.md) | Per-agent Gemini config |
| Project DNA | [`AGENTS.md`](AGENTS.md) | Hard rules (non-negotiable) |

When behaviour changes, update [`specs/`](specs/) **before** generating code,
then write a test under `backend/tests/` before the implementation. See
[`AGENTS.md`](AGENTS.md#adding-a-new-feature) for the full workflow and
[`specs/README.md`](specs/README.md) for the spec → test mapping.

---

## Key design decisions

- **LLM calls are minimal by design.** Agents 1, 3, 4, 5 are LLM agents.
  Agent 2 uses deterministic tool calls (curated CSV → SQLite FTS → fuzzy
  match → RxNav). Guardrails run as callbacks, not inside agent prompts.
  LLM-as-Judge scoring runs asynchronously after the response — it never
  blocks the patient.

- **Memory stores resolved drug names, not prescriptions.** Vertex AI Memory
  Bank stores generic names, visit timestamp, and severity summary only.
  It never stores prescription images, clinical notes, diagnoses, or raw
  model output.

- **The auth broker is the only public surface.** Agent Runtime is private
  and only reachable via service-account credentials. Images travel client
  → GCS signed URL → Agent 1 (`Part.from_uri`), never through the broker
  payload.

- **Drug data is built, not hard-coded.** Lookup goes through five
  deterministic tiers before falling back to RxNav; see
  [`AGENTS.md`](AGENTS.md#drug-data-sources). Quality is gated by
  `backend/tests/test_drug_lookup_eval.py`.

- **Agent boundaries are explicit.** Each agent's inputs, outputs, and
  forbidden actions are declared in
  [`specs/agent_boundaries.yaml`](specs/agent_boundaries.yaml). Tools are
  leaf nodes — they never call other agents.

---

## Out of scope

See [`docs/out_of_scope.md`](docs/out_of_scope.md) for the full list. Notable
exclusions: a clinical interaction database (LLM pharmacological knowledge is
used today as an acceptable POC tradeoff), dose-adjustment advice, a
doctor-facing interface, and clinical-trial matching.

---

## Contributing

Contributions are welcome. Please read [`CONTRIBUTING.md`](CONTRIBUTING.md)
and our [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) first.

Before opening a PR:

1. Update [`specs/`](specs/) if you are changing behaviour.
2. Update [`AGENTS.md`](AGENTS.md) if you are changing a rule or boundary.
3. Add or update tests under `backend/tests/`.
4. Run `uv run pytest tests/unit tests/integration` — all tests must pass.

For production-incident debugging, use the evidence-driven templates in
[`docs/forensic_prompts.md`](docs/forensic_prompts.md).

---

## Security

Please **do not** open public issues for security vulnerabilities. Follow the
disclosure process in [`SECURITY.md`](SECURITY.md).

---

## Acknowledgements

This project began as a capstone for the 2026 Kaggle 5-Day AI Agents Intensive.
It builds on:

- [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/)
- [Google Gemini](https://ai.google.dev/) (3.1 Flash / Flash Lite)
- [RxNav / RxNorm](https://lhncbc.nlm.nih.gov/RxNav/) for fallback drug normalisation
- Indian medicine datasets on Kaggle — [Indian Medicine Data](https://kaggle.com/datasets/mohneesh7/indian-medicine-data), [Extensive A–Z Medicines Dataset of India](https://kaggle.com/datasets/riturajsingh2004/extensive-a-z-medicines-dataset-of-india), [All India Drug Bank Database](https://kaggle.com/datasets/ankushpoddar/all-india-drug-bank-database) (see [Drug data sources](#drug-data-sources))

---

## Disclaimer

This is an **educational prototype**. It is **not a medical device**, **not a
substitute for pharmacist or doctor advice**, and **has not been clinically
validated**. Do not use it for real medical decisions.

---

## License

[MIT](LICENSE)
