# 💊 Medication Companion

> **Kaggle 5-Day AI Agents Intensive 2026 — Capstone Project**  
> A multi-agent AI system that helps patients in India understand prescriptions and stay safe across multiple visits and multiple doctors.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Flutter](https://img.shields.io/badge/Flutter-3.x-02569B?logo=flutter)](https://flutter.dev)
[![Google ADK](https://img.shields.io/badge/Google%20ADK-latest-4285F4)](https://google.github.io/adk-docs/)
[![GCP](https://img.shields.io/badge/GCP-Cloud%20Run-orange)](https://cloud.google.com/run)

---

## What it does

A patient photographs their prescription. The system:

1. **Reads** the prescription image — extracts drug names using Gemini Vision (Agent 1)
2. **Resolves** brand → generic names, splits fixed-dose combinations (Agent 2)
3. **Checks safety** — flags interactions against current AND past medications from memory (Agent 3)
4. **Explains** the findings in plain, calibrated language appropriate to severity (Agent 4)
5. **Localises** the explanation into the patient's language and generates audio (Agent 5, via A2A)

> ⚠️ **This is not a medical device.** Every output directs the patient back to their doctor or pharmacist. This is an educational prototype, not a substitute for professional medical advice.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Flutter PWA (Firebase Hosting)                │
│  Login → Upload Prescription → View Results + Audio Player           │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ POST /agent/run  (Firebase Auth JWT)
┌──────────────────────────────▼──────────────────────────────────────┐
│              Cloud Run: medication-companion (FastAPI + ADK)          │
│                                                                       │
│  Guard ──► Agent 1 ──► Agent 2 ──► Agent 3 ──► Agent 4 ──► Guard    │
│  (Input)   (Reader)   (Resolver)  (Safety)   (Education)  (Output)  │
│                │           │          │                               │
│                │    FunctionTools  MemoryBank                        │
│                │    RxNav API      VertexAI Session                  │
│                └──────────────────────────────────────┐              │
└──────────────────────────────────────────────────────┼──────────────┘
                                                        │ A2A Protocol
┌──────────────────────────────────────────────────────▼──────────────┐
│              Cloud Run: medication-companion-a2a (Agent 5)            │
│              Localisation + Text-to-Speech → GCS MP3 → Signed URL    │
└─────────────────────────────────────────────────────────────────────┘
```

**GCP Services:** Cloud Run · Vertex AI Agent Engine · Cloud Storage · Cloud Text-to-Speech · BigQuery · Firebase Auth · Firebase Hosting · Cloud Trace

---

## Course alignment (2026 Kaggle AI Agents Intensive)

| Day | Topic | Where it appears |
|-----|-------|-----------------|
| **Day 1** | Agents & Vibe Coding | Multi-agent pipeline; autonomous Gate 1 rejection in Agent 1; `.cursor/rules/` spec-driven generation |
| **Day 2** | Tools & Interoperability (MCP + A2A) | `FunctionTool`s in Agent 2 (RxNav, combo-splitter); Agent 5 as independent A2A service with Agent Card |
| **Day 3** | Context Engineering (Memory & Sessions) | `VertexAiSessionService` carries session state; `VertexAiMemoryBankService` stores cross-visit drug history |
| **Day 4** | Agent Quality (Guardrails + Eval) | Input/output guardrail callbacks; LLM-as-Judge scorer writing to BigQuery |
| **Day 5** | Spec-Driven Production Development | `.cursor/rules/medication-companion.mdc`; two Cloud Run services; Cloud Trace; `deploy/deploy.sh` |

---

## Quick start (local development)

### Prerequisites

- Python 3.11+
- Flutter 3.x
- Google Cloud SDK (`gcloud`)
- A GCP project with billing enabled

### Backend (agents, no GCP credentials needed)

```bash
cd backend
pip install -r requirements.txt

# Run with in-memory session/memory backend (no GCP needed)
MEMORY_BACKEND=local GEMINI_MODEL=gemini-2.0-flash python -m uvicorn main:app --reload
```

### Kaggle notebook (demo)

Open `notebooks/medication_companion_demo.ipynb` — runs all 5 agents with `InMemorySessionService`, no GCP credentials required.

### Full GCP deployment

```bash
# 1. Set your project
gcloud config set project YOUR_PROJECT_ID

# 2. Create all GCP resources (one-time setup)
./scripts/setup_gcp.sh

# 3. Deploy both Cloud Run services + Firebase Hosting
./deploy/deploy.sh
```

---

## Repository layout

```
medication-companion/
├── backend/                        # Python — ADK agents + FastAPI
│   ├── agents/
│   │   ├── agent1_reader.py        # Prescription Reader (Gemini Vision)
│   │   ├── agent2_resolver.py      # Medication Resolver (RxNav + India CSV)
│   │   ├── agent3_safety.py        # Reconciliation + Safety (core value)
│   │   ├── agent4_education.py     # Patient Education
│   │   └── agent5_localisation.py  # Localisation + Audio (A2A server)
│   ├── tools/
│   │   ├── drug_lookup.py          # FunctionTool: brand → generic (RxNav)
│   │   ├── combo_splitter.py       # FunctionTool: split combination drugs
│   │   ├── tts.py                  # FunctionTool: GCP Text-to-Speech
│   │   └── guardrails.py           # Input/output safety callbacks (Day 4)
│   ├── memory/
│   │   ├── session_service.py      # ADK VertexAiSessionService wrapper
│   │   └── memory_service.py       # ADK VertexAiMemoryBankService wrapper
│   ├── evaluation/
│   │   └── llm_judge.py            # LLM-as-Judge scorer → BigQuery (Day 4)
│   ├── tests/                      # pytest unit + integration tests
│   ├── main.py                     # FastAPI app (get_fast_api_app)
│   ├── a2a_server.py               # Agent 5 A2A service entry point
│   ├── Dockerfile
│   ├── Dockerfile.a2a
│   └── requirements.txt
├── frontend/                       # Flutter PWA
│   ├── lib/
│   │   ├── auth/                   # Firebase Auth
│   │   ├── screens/                # Login, Home, Upload, Result
│   │   ├── services/               # API service (attaches JWT)
│   │   └── models/                 # PrescriptionResult model
│   ├── web/
│   │   └── index.html              # PWA manifest + service worker
│   └── pubspec.yaml
├── deploy/
│   ├── deploy.sh                   # Full deployment (Cloud Run + Firebase)
│   └── firestore.rules
├── scripts/
│   ├── setup_gcp.sh                # One-time GCP project setup + resource creation
│   └── teardown_gcp.sh             # Clean up all GCP resources
├── data/
│   └── india_brands.csv            # 200+ Indian brand → generic mappings
├── notebooks/
│   └── medication_companion_demo.ipynb  # Kaggle submission notebook
├── docs/
│   ├── architecture.md             # Detailed architecture decisions
│   ├── agent_design.md             # Per-agent spec and boundaries
│   └── out_of_scope.md             # Explicit scope decisions for judges
├── .cursor/
│   └── rules/
│       └── medication-companion.mdc  # Spec-driven development rules (Day 5)
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                  # Lint + test on PR
│   │   └── deploy.yml              # Deploy on merge to main
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.md
│       └── feature_request.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── SECURITY.md
├── LICENSE
└── README.md
```

---

## Key design decisions

**LLM calls are minimal by design.** Agents 1, 3, 4, 5 are LLM agents. Agent 2 uses deterministic tool calls (RxNav API + CSV). Guardrails run as callbacks, not inside agent prompts. LLM-as-Judge runs async after the response — it never blocks the patient.

**Agent 5 is a separate service (A2A) by design.** Localisation is genuinely independent — it could be replaced with a specialist translation service without touching Agents 1–4. This is not over-engineering; it demonstrates the Day 2 A2A protocol deliberately.

**Memory stores drug names, not prescriptions.** `VertexAiMemoryBankService` stores resolved generic names + visit timestamp + severity summary. It never stores: prescription images, clinical notes, diagnosis text, raw LLM output.

---

## Out of scope (explicit — judges value clear boundaries)

See [`docs/out_of_scope.md`](docs/out_of_scope.md) for the full list. Key exclusions: clinical interaction database (LLM pharmacological knowledge is used — acceptable for POC), dose adjustment advice, doctor-facing interface, clinical trial matching.

---

## Disclaimer

This is an educational prototype built for the Kaggle 5-Day AI Agents Intensive 2026. It is **not a medical device**, **not a substitute for pharmacist or doctor advice**, and has **not been clinically validated**. Do not use for real medical decisions.

---

## License

MIT — see [LICENSE](LICENSE)
