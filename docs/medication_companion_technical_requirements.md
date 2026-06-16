# Medication Companion — Technical Requirements Document

> Feed this document to Cursor as your primary spec.  
> It describes what to build, how it maps to the 2026 Kaggle course, and all implementation decisions.

---

## 1. What we are building

A multi-agent AI system that helps patients in India understand their prescriptions and stay safe across multiple visits and multiple doctors.

A patient photographs their prescription. The system:
1. Reads and resolves the drug names (brand → generic, combos split)
2. Compares them against the patient's medication history across all past visits
3. Flags interactions: new drugs against each other AND against prior medications
4. Explains the findings in plain language, tone calibrated to severity
5. Translates the explanation into the patient's language and generates audio

This is not a diagnostic tool. Every output directs the patient back to their doctor.

---

## 2. Repository layout

```
medication-companion/
├── backend/                        # Python — ADK agents + FastAPI
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── agent1_reader.py        # Prescription Reader
│   │   ├── agent2_resolver.py      # Medication Resolver
│   │   ├── agent3_safety.py        # Reconciliation + Safety (core value)
│   │   ├── agent4_education.py     # Patient Education
│   │   └── agent5_localisation.py  # Localisation + Audio (A2A server)
│   ├── tools/
│   │   ├── drug_lookup.py          # FunctionTool: brand → generic
│   │   ├── combo_splitter.py       # FunctionTool: split combination drugs
│   │   ├── tts.py                  # FunctionTool: GCP Text-to-Speech
│   │   └── guardrails.py           # Input/output safety filters (Day 4)
│   ├── memory/
│   │   ├── session_service.py      # ADK VertexAiSessionService wrapper
│   │   └── memory_service.py       # ADK VertexAiMemoryBankService wrapper
│   ├── evaluation/
│   │   └── llm_judge.py            # LLM-as-Judge scorer (Day 4)
│   ├── main.py                     # FastAPI app using get_fast_api_app()
│   ├── a2a_server.py               # Agent 5 as separate A2A service (Day 2)
│   ├── Dockerfile
│   ├── Dockerfile.a2a              # Separate image for Agent 5
│   └── requirements.txt
├── frontend/                       # Flutter PWA
│   ├── lib/
│   │   ├── main.dart
│   │   ├── auth/
│   │   │   └── firebase_auth_service.dart
│   │   ├── screens/
│   │   │   ├── login_screen.dart
│   │   │   ├── home_screen.dart
│   │   │   ├── upload_screen.dart
│   │   │   └── result_screen.dart
│   │   ├── services/
│   │   │   └── api_service.dart    # calls FastAPI backend
│   │   └── models/
│   │       └── prescription_result.dart
│   ├── web/
│   │   └── index.html              # PWA manifest + service worker ref
│   └── pubspec.yaml
├── deploy/
│   ├── deploy.sh                   # gcloud commands — both Cloud Run services
│   └── firestore.rules             # Firestore security rules
├── .cursor/
│   └── rules/
│       └── medication-companion.mdc  # Cursor rules — the "spec" in spec-driven development
└── README.md
```

---

## 3. Day-by-day course alignment

This is the rationale section for the Kaggle writeup. Every course day must be demonstrably present in the code.

### Day 1 — Agents & Vibe Coding

**What it covers:** Agentic vs single LLM call. Autonomous decision-making. Vibe coding = natural language as the primary spec-to-code interface.

**Where it appears:**

Agent 1 (`agent1_reader.py`) demonstrates the core agentic difference. A single LLM call would accept any image and produce a best-guess output. Agent 1 evaluates OCR confidence per drug name and makes an autonomous branch decision: if any name scores below threshold, it rejects the prescription and asks the patient to retake the photo. This is Gate 1 — not a filter applied after the fact, but a decision that stops the pipeline before downstream agents process garbage input.

The multi-agent pipeline itself is the Day 1 argument: five agents with distinct responsibilities, each making decisions and passing structured state forward. No single LLM prompt could do what Agent 3 does (compare against a patient's full medication history retrieved from memory) in one call.

**Vibe coding angle:** The agents in this project were spec-written in natural language (this document) and then generated with Cursor using that spec as primary context. The `.cursor/rules/medication-companion.mdc` file encodes domain constraints (no diagnostic language, always redirect to doctor) so Cursor generates safe, scoped output by default. This is the vibe coding workflow: English spec → Cursor → production-shaped code.

**Implementation note:**
```python
# agent1_reader.py
# ADK LlmAgent with Gemini Vision
# Decision logic: if any drug name confidence < 0.75, return Gate1Reject
# Gate1Reject triggers a user-facing message and halts the pipeline
```

---

### Day 2 — Tools & Interoperability (MCP + A2A)

**What it covers:** External APIs as FunctionTools, MCP for tool discovery and connection, Agent-to-Agent (A2A) protocol for interoperability between independent agent services.

The Day 2 paper covers both MCP and A2A explicitly. Both are present here.

**MCP / FunctionTools — Agent 2:**

Agent 2 (`agent2_resolver.py`) uses two registered `FunctionTool`s:

- `drug_lookup` — calls RxNav API (`https://rxnav.nlm.nih.gov/REST/`) to resolve brand name to generic. Falls back to a bundled Indian brand CSV for names not in RxNav (Indian generics and combos are poorly covered by RxNav).
- `combo_splitter` — splits combination products into their active components. Example: Pantocid DSR → pantoprazole 40mg + domperidone 10mg. This is a local lookup table seeded from CIMS India data.

These are tools the agent *decides to call* — not hardcoded function calls. Agent 2 receives a list of extracted drug names and independently determines which ones need combo splitting vs direct lookup.

**A2A protocol — Agent 4 → Agent 5:**

Agent 5 (Localisation + Audio) is deployed as a *separate* Cloud Run service with its own Agent Card at `/.well-known/agent.json`. Agent 4 sends the completed English explanation to Agent 5 via the A2A protocol using ADK's `to_a2a()` wrapper.

This demonstrates the Day 2 paper's A2A story: two independently deployed agents from different "domains" (explanation generation vs localisation/audio) communicating via a standard protocol. Neither needs to know how the other is implemented. Agent 5 could be replaced with a different localisation service without changing Agent 4 at all.

The A2A handoff carries:
- `explanation_text`: the English explanation from Agent 4
- `target_language`: patient's language preference (hi-IN, ta-IN, te-IN, bn-IN, en-IN)
- `severity`: passed through so Agent 5 knows whether to add urgent tone markers

Agent 5 internal flow:
1. Translate explanation text (Gemini with language instruction)
2. Call GCP Text-to-Speech via `FunctionTool` → MP3 bytes
3. Upload MP3 to Cloud Storage
4. Return signed URL to Agent 4 via A2A response

**Implementation note:**
```python
# tools/drug_lookup.py
# FunctionTool wrapping RxNav rxcui lookup + fallback CSV
# Input: brand_name: str
# Output: {"generic": str, "drug_class": str, "confidence": float}

# tools/combo_splitter.py
# FunctionTool wrapping local combo lookup table
# Input: drug_name: str
# Output: list[{"component": str, "dose": str}]

# a2a_server.py
# Agent 5 as A2A server using to_a2a() wrapper
# Serves: POST /a2a  (A2A task endpoint)
# Serves: GET /.well-known/agent.json  (Agent Card)

# tools/tts.py
# FunctionTool wrapping google.cloud.texttospeech
# Supported: hi-IN, ta-IN, te-IN, bn-IN, en-IN
# Output: GCS signed URL, expires 24h
```

---

### Day 3 — Agent Skills (Memory & Long Context)

**What it covers:** Long-term memory, session state, skills as reusable agent capabilities composable across frameworks.

**Where it appears:**

This is the most important day for this project because it is what makes Agent 3's core safety check possible.

**Short-term session (within a single pipeline run):**
`VertexAiSessionService` carries the resolved drug list produced by Agent 2 into Agent 3 without re-processing. The session holds structured state: resolved medicines, confidence scores, Gate 1 result. Agent 3 reads from session state rather than re-calling Agent 2.

**Long-term memory (across visits):**
`VertexAiMemoryBankService` stores the patient's resolved medication list from each completed visit. At the start of Agent 2, a `PreloadMemoryTool` retrieves the patient's known medication history from Memory Bank. Agent 2 tags each resolved drug as `NEW` (this prescription) or `EXISTING` (appears in memory from prior visits).

Agent 3 then runs two checks:
- **NEW vs NEW**: are any drugs in the current prescription problematic together?
- **NEW vs EXISTING**: do any new drugs interact with what the patient is already taking?

The second check is *only possible because of the memory layer*. Without it, Agent 3 can only do half its job. This is the architectural argument for why this had to be built as an agent system with memory, not a single LLM call.

After Agent 4 completes, an `after_agent_callback` calls `add_session_to_memory()` to persist this visit's resolved medications for future use.

**Skills framing:**
Each agent capability (brand resolution, interaction checking, explanation generation, localisation) is a reusable, independently deployable skill. They are composable: the drug resolution skill is independent of the safety check skill, which is independent of the localisation skill. The memory layer is what binds them into a personalised experience across visits.

**Implementation note:**
```python
# memory/session_service.py
# Wraps VertexAiSessionService
# Session keys: patient_id, resolved_drugs, gate1_result, visit_timestamp

# memory/memory_service.py
# Wraps VertexAiMemoryBankService
# PreloadMemoryTool: retrieves prior medications at start of Agent 2
# after_agent_callback: persists this visit after Agent 4 completes successfully

# agent3_safety.py
# Reads session state (resolved_drugs tagged NEW/EXISTING)
# Check 1: NEW vs NEW interaction scan
# Check 2: NEW vs EXISTING interaction scan
# Returns severity: HIGH | MODERATE | LOW | INFO | NONE
# Returns structured findings: {drug_a, drug_b, severity, mechanism, plain_english}
```

---

### Day 4 — Vibe Coding Agent Security and Evaluation

**What it covers:** Guardrails, security against prompt injection and scope creep, LLM-as-Judge evaluation, observability, quality metrics.

**Where it appears:**

**Security / guardrails (`tools/guardrails.py`):**

Input guardrails (before Agent 1):
- Reject images that are clearly not prescriptions (no drug names detected)
- Reject requests containing dosing advice questions ("how much should I take")
- Reject requests containing diagnostic questions ("do I have X disease")
- Prompt injection detection: reject inputs with instruction-override patterns

Output guardrails (after Agent 4):
- Scan output for diagnostic language and strip it
- Ensure every output includes a "consult your doctor" redirect
- Ensure drug names in the explanation match the resolved drug list (hallucination check — no invented drugs in output)

This is the Day 4 security story specific to a medical-adjacent tool: scope enforcement is non-negotiable. A guardrail that runs as a callback is architecturally cleaner than baking safety instructions into every prompt.

**Evaluation (`evaluation/llm_judge.py`):**

After every pipeline run, a separate LLM-as-Judge call scores the output on two dimensions:

1. **Safety completeness (0–10):** Did the agent surface all interactions it should have? The judge receives the resolved drug list and the interaction findings and asks: "Are there clinically notable interactions here that were missed?"

2. **Explanation clarity (0–10):** Would a patient with no medical background understand this? The judge receives the explanation text and scores readability and actionability.

Both scores are written to BigQuery with session ID, timestamp, and agent versions. This is the audit trail — retrospective analysis of where the pipeline underperforms.

**Observability:**
Cloud Trace instruments each agent as a named span. The full pipeline trace (Agent 1 → Agent 5 via A2A) is visible as a waterfall in Cloud Trace. Slow agents and failure rates are immediately visible without log mining.

**Implementation note:**
```python
# tools/guardrails.py
# before_agent_callback: input validation + scope check + injection detection
# after_agent_callback: output scan + disclaimer injection + hallucination check

# evaluation/llm_judge.py
# Called async after Agent 4 output — does not block the response to the patient
# Returns: {safety_score: int, clarity_score: int, flags: list[str]}
# Writes to BigQuery: medication_companion.eval_log
```

---

### Day 5 — Spec-Driven Production Grade Development

**What it covers:** Graduating local agents into a governed, scalable, observable production fleet. Cloud deployment, debugging, structured logging, the "spec-driven" development story.

**Where it appears:**

**Spec-driven development:**
The `.cursor/rules/medication-companion.mdc` file is the "spec" that governed how all agent code in this project was generated. It encodes: safety language rules, agent boundary rules (no agent may perform another's responsibility), memory rules, code style constraints. This is not documentation added after the fact — it was the primary input to Cursor before any code was written. Every agent file, every tool, was generated with these rules active.

This is the Day 5 concept: the spec precedes the code, and the spec is machine-readable (Cursor enforces it). Vibe coding at scale requires this governance layer, otherwise natural language prompts drift toward unsafe or inconsistent output.

**Production deployment:**
Two Cloud Run services — the main pipeline (Agents 1–4 + FastAPI) and the A2A localisation service (Agent 5) — each with their own Dockerfile, independently deployable and scalable. The `deploy/deploy.sh` script captures the full deployment sequence reproducibly.

**Observability fleet:**
- Cloud Trace: distributed tracing across both Cloud Run services including the A2A call
- Structured JSON logging (not print statements) so Cloud Logging can parse and filter
- BigQuery eval log as the long-term quality audit store
- Health endpoints (`GET /health`) on both services for Cloud Run health checks

**Implementation note:**
```python
# main.py
# Uses get_fast_api_app() from google.adk.cli.fast_api
# Structured logging: google.cloud.logging
# Cloud Trace: opentelemetry-sdk + google-cloud-trace exporter
# Health: GET /health → {"status": "healthy", "version": "..."}

# deploy/deploy.sh
# Reproducible: gcloud run deploy with explicit image tags, not :latest
# Both services deployed with --no-allow-unauthenticated
# Firebase Auth JWT validated at FastAPI middleware layer
```

---

## 4. Backend — FastAPI + ADK

### Entry point (`main.py`)

```python
# Uses get_fast_api_app() from google.adk.cli.fast_api
# Mounts agents 1–4 under /agent
# Firebase Auth middleware: validate ID token on every non-health request
# Health endpoint: GET /health
# Swagger: GET /docs (disabled in production via ENVIRONMENT=prod check)
```

### Agent pipeline flow

```
POST /precription  (multipart/form-data: image file)
  → Firebase ID token validated (middleware) → patient_id = uid
  → image uploaded to GCS (returns gs:// URI)
  → Agent 1: image → raw drug names + Gate 1 decision
  → if Gate 1 reject: return 422 {"error": "retake_required", "message": "..."}
  → Agent 2: names → generics (FunctionTool calls) + PreloadMemory (EXISTING tagging)
  → Agent 3: safety check (NEW vs NEW, NEW vs EXISTING) → severity + findings
  → Agent 4: explanation generation → after_agent_callback writes memory
  → LLM Judge: async background task (does not block response)
  → A2A call to Agent 5: translated text + audio URL
  → return PrescriptionResult JSON
```

### PrescriptionResult schema

```python
class PrescriptionResult(BaseModel):
    session_id: str
    resolved_drugs: list[ResolvedDrug]          # name, generic, status: NEW|EXISTING|UNRESOLVED
    interactions: list[InteractionFinding]       # drug_a, drug_b, severity, mechanism, plain_english
    overall_severity: Literal["HIGH", "MODERATE", "LOW", "INFO", "NONE"]
    explanation_en: str
    explanation_localised: str
    audio_url: str                               # GCS signed URL, 24h expiry
    doctor_questions: list[str]
    disclaimer: str
    eval_scores: EvalScores | None              # null until async eval completes
```

---

## 5. Memory architecture decision

Two memory concerns, two mechanisms:

| Concern | Mechanism | Why |
|---|---|---|
| State within one pipeline run | `VertexAiSessionService` | Agents share resolved drug list without re-calling each other |
| Medication history across visits | `VertexAiMemoryBankService` | Persistent, semantically searchable — handles brand/generic name variation |

**Why not Firestore for memory?**
Firestore is used for auth (Firebase) and user preferences. For medication memory, `VertexAiMemoryBankService` is correct because it does semantic retrieval — if a patient's prior entry says "amlodipine" and the new prescription says "Amlodip", Memory Bank finds the match. A Firestore exact-key lookup cannot do this.

**Local dev fallback:**
`InMemorySessionService` and `InMemoryMemoryService` for running without GCP credentials. Controlled by `MEMORY_BACKEND=local|vertex` env var.

---

## 6. Auth

### Capstone scope (build now)

Firebase Authentication with email/password.

**Flutter side:**
- `firebase_auth` package
- `FirebaseAuth.instance.createUserWithEmailAndPassword()` for signup
- `FirebaseAuth.instance.signInWithEmailAndPassword()` for login
- `user.getIdToken()` → Firebase ID token (JWT) attached as `Authorization: Bearer <token>`

**Backend side:**
- FastAPI middleware validates token via `firebase-admin`: `auth.verify_id_token(token)`
- Extracts `uid` as `patient_id` — the single key for all memory lookups
- Returns 401 if token invalid or expired

**Firestore security rules:**
```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /users/{userId}/{document=**} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
  }
}
```

### Production extension path (document in writeup, do not build now)

- Google Sign-In (one-tap — most common in India)
- Phone OTP (Firebase-native, very high coverage in India)
- Clinic SSO via SAML for EMR integration

The `patient_id == Firebase UID` abstraction means adding any of these changes only the Flutter auth screen. No agent code changes.

---

## 7. Frontend — Flutter PWA

### What to build

4-screen PWA. Flutter Web compiled to static files, served from Firebase Hosting (simpler than Cloud Run for static assets).

### Screens

**Login (`login_screen.dart`)**
- Email + password, sign in / create account tabs
- Firebase Auth calls → Home screen on success

**Home (`home_screen.dart`)**
- Patient name from Firebase display name
- Last visit summary card: date, drug count, severity badge
- "Analyse new prescription" CTA → Upload screen
- Language preference selector (stored in Firestore user doc: `users/{uid}/preferences`)

**Upload (`upload_screen.dart`)**
- Camera capture or gallery pick (`image_picker` package)
- Preview with "looks clear?" confirmation
- Submit → `POST /agent/run`
- Loading state with step progress: "Reading prescription..." → "Checking interactions..." → "Generating audio..."
- 422 handling: show "Photo wasn't clear enough, please retake" with camera button

**Result (`result_screen.dart`)**
- Severity banner (HIGH=red, MODERATE=amber, LOW=green, INFO/NONE=blue)
- Drug cards: name, generic equivalent, NEW/EXISTING badge
- Interaction cards: drug pair, severity chip, plain-language mechanism
- Full explanation text
- Audio player (`audioplayers` package, plays GCS signed URL)
- "Questions to ask your doctor" list
- Disclaimer footer

### API service (`services/api_service.dart`)

```dart
// Attaches Firebase ID token as Bearer header on every call
// POST /agent/run → multipart/form-data (image bytes)
// Returns PrescriptionResult
// 422 → retake flow
// 401 → re-auth flow
// Network timeout: 60s (pipeline can take ~15-20s)
```

### PWA config (`web/index.html`)
- Manifest: `display: standalone`, `theme_color` per severity
- Service worker: offline shell caching (not offline functionality — just prevents blank screen)

---

## 8. GCP infrastructure

### Services required

| Service | Purpose |
|---|---|
| Cloud Run (service 1) | Agents 1–4 + FastAPI — `medication-companion` |
| Cloud Run (service 2) | Agent 5 A2A server — `medication-companion-a2a` |
| Cloud Storage | Prescription images + audio MP3s |
| Vertex AI Agent Engine | `VertexAiSessionService` + `VertexAiMemoryBankService` |
| Cloud Text-to-Speech | Audio generation in Agent 5 |
| BigQuery | Eval scores + pipeline audit log |
| Firebase Auth | Email/password authentication |
| Firebase Hosting | Flutter PWA static files |
| Cloud Trace | Distributed tracing — both services + A2A call |

### Environment variables (backend)

```bash
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
AGENT_RUNTIME_ID=your-agent-runtime-id     # from Vertex AI Agent Engine setup
GCS_BUCKET=medication-companion-uploads
A2A_AGENT5_URL=https://medication-companion-a2a-xyz.run.app
MEMORY_BACKEND=vertex                       # local for dev
GEMINI_MODEL=gemini-2.0-flash
FIREBASE_PROJECT_ID=your-project-id
BIGQUERY_DATASET=medication_companion
ENVIRONMENT=production                      # disables Swagger
LOG_LEVEL=INFO
```

### Deployment (`deploy/deploy.sh`)

```bash
#!/bin/bash
set -e

PROJECT_ID=$(gcloud config get-value project)
REGION=us-central1
GCS_BUCKET=medication-companion-uploads

# Enable required APIs
gcloud services enable \
  aiplatform.googleapis.com \
  run.googleapis.com \
  storage.googleapis.com \
  texttospeech.googleapis.com \
  bigquery.googleapis.com \
  cloudtrace.googleapis.com \
  firebase.googleapis.com

# GCS bucket
gsutil mb -l $REGION gs://$GCS_BUCKET || true

# BigQuery
bq mk --dataset $PROJECT_ID:medication_companion || true
bq mk --table $PROJECT_ID:medication_companion.eval_log \
  session_id:STRING,timestamp:TIMESTAMP,patient_id:STRING,\
  safety_score:INTEGER,clarity_score:INTEGER,flags:STRING,\
  agent_versions:STRING || true

# Deploy Agent 5 A2A service first (main service needs its URL)
gcloud run deploy medication-companion-a2a \
  --source ./backend \
  --dockerfile backend/Dockerfile.a2a \
  --region $REGION \
  --no-allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT_ID,ENVIRONMENT=production

A2A_URL=$(gcloud run services describe medication-companion-a2a \
  --region $REGION --format 'value(status.url)')

# Deploy main service (Agents 1-4)
gcloud run deploy medication-companion \
  --source ./backend \
  --dockerfile backend/Dockerfile \
  --region $REGION \
  --no-allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT_ID,A2A_AGENT5_URL=$A2A_URL,ENVIRONMENT=production

# Deploy Flutter PWA
cd frontend
flutter build web --release
firebase deploy --only hosting
```

---

## 9. Cursor rules file

Create `.cursor/rules/medication-companion.mdc`. This is the spec artefact for Day 5 — it governs all code Cursor generates in this project.

```markdown
---
name: medication-companion
description: Domain and code rules for Medication Companion. Apply to all files in this project.
---

## Safety language — enforce in all agent outputs
- Never use diagnostic language: "you have", "this indicates", "this means you have"
- Every patient-facing string must end with a consult-your-doctor redirect
- Severity values are exactly: HIGH, MODERATE, LOW, INFO, NONE — no others
- HIGH means "worth discussing urgently with your doctor", not "dangerous"
- LOW and INFO must still include the consult redirect — do not omit it

## Interaction checking scope
- Check interactions only for drugs confirmed in the resolved drug list
- Do not speculate about interactions with drugs not in the list
- If interaction data is unavailable for a pair: output INFO + "insufficient data to assess"
- Never invent drug names in explanations — output must only reference resolved_drugs

## Agent boundaries — no agent may cross these
- Agent 1: image extraction only — no resolution, no safety checking
- Agent 2: resolution and EXISTING/NEW tagging only — no safety checking
- Agent 3: safety checking only — no explanation generation
- Agent 4: explanation only — no new safety checking, no new drug resolution
- Agent 5: localisation and audio only — no content changes to explanation text
- Guardrails run as callbacks, not inside agent logic

## Memory rules
- patient_id is always the Firebase UID extracted from the verified ID token
- Memory writes occur only after Agent 4 completes successfully (after_agent_callback)
- Memory stores only: resolved generic drug names, visit timestamp, severity summary
- Memory never stores: image data, clinical notes, diagnosis text, raw LLM output

## Code rules
- All agents: google.adk LlmAgent — no raw Gemini API calls
- All tools: google.adk FunctionTool with complete type hints and docstrings
- All inter-agent data: Pydantic BaseModel — no plain dicts across boundaries
- Async throughout: async def, await, no blocking calls in agent handlers
- Structured logging: google.cloud.logging — no print() in production code paths
- MEMORY_BACKEND env var controls session/memory backend: "local" or "vertex"

## Security rules
- Input guardrail runs before Agent 1 on every request
- Output guardrail runs after Agent 4 before returning to client
- Prompt injection patterns in input → reject with 400, do not process
- Diagnostic questions in input → reject with 400 + "consult your doctor" message
```

---

## 10. Indian drug name handling

RxNav covers US generics well but Indian brand names poorly. Fixed-dose combinations (FDCs) are very common in India and must be split before interaction checking.

**Bundled CSV (`data/india_brands.csv`):**

Seed with minimum 200 entries covering:
- Antibiotics: Azee (azithromycin), Augmentin (amoxicillin+clavulanate), Ciplox (ciprofloxacin), Taxim (cefotaxime)
- Combos: Pantocid DSR (pantoprazole+domperidone), Dolo 650 (paracetamol 650mg), Combiflam (ibuprofen+paracetamol), Cheston Cold (cetirizine+paracetamol+pseudoephedrine)
- Cardiovascular: Amlodip/Amlokind (amlodipine), Metolar (metoprolol), Aten (atenolol), Telma (telmisartan)
- Diabetes: Glycomet (metformin), Voglitor (voglibose+metformin), Januvia (sitagliptin)
- Analgesics: Voveran (diclofenac), Zerodol (aceclofenac), Hifenac (aceclofenac+paracetamol)
- Blood thinners / cardiac: Ecosprin (aspirin), Deplatt (clopidogrel), Cardivas (carvedilol)

Runtime lookup order: RxNav API → local CSV → tag as UNRESOLVED.

**Production extension (not in capstone scope):** CIMS India API, 1mg drug database, or OpenFDA with India-specific supplement.

---

## 11. What is NOT in scope for capstone

State these explicitly in the Kaggle writeup. Judges respect clear scope decisions.

- No clinical interaction database (using LLM's pharmacological knowledge — acceptable for POC, production would use DrugBank or similar)
- No image pre-processing or OCR enhancement pipeline
- No structured storage of full prescription history (memory stores drug names, not images or complete prescription data)
- No pharmacy or dispensing integration
- No doctor-facing interface
- No dose adjustment advice of any kind
- No refill reminders or adherence tracking
- No real-time drug pricing
- No clinical trial matching

---

## 12. Kaggle submission checklist

- [ ] Kaggle notebook demonstrating all 5 agents (use `InMemorySessionService` for notebook — no GCP credentials needed)
- [ ] GitHub repo (public) with full source code
- [ ] Video walkthrough (~3 min): prescription photo → result screen → audio playback in Hindi or Tamil
- [ ] Writeup: one paragraph per course day mapping to concrete code artefacts
- [ ] Deployed demo URL (Cloud Run + Firebase Hosting) — judges strongly favour live demos
- [ ] Disclaimer prominent in writeup: educational prototype, not a medical device, not a substitute for pharmacist or doctor advice

---

## 13. Local development setup

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

export MEMORY_BACKEND=local
export GEMINI_API_KEY=your-key
export GOOGLE_CLOUD_PROJECT=your-project-id
export FIREBASE_PROJECT_ID=your-project-id

# Run main service
uvicorn main:app --reload --port 8080

# Run A2A service (separate terminal)
uvicorn a2a_server:app --reload --port 8081

# Flutter PWA
cd frontend
flutter pub get
flutter run -d chrome         # dev mode
flutter build web --release   # production build → build/web/
```

**Local testing without GCP:**
- `MEMORY_BACKEND=local` → `InMemorySessionService` + `InMemoryMemoryService`
- Drug lookup uses bundled CSV only (no RxNav call needed)
- TTS tool returns a stub MP3 URL when `ENVIRONMENT=local`
- Firebase Auth validation can be bypassed in local mode with a `DEV_PATIENT_ID` env var

---

## 14. Build order for Cursor

Build and test in this order. Each step is independently runnable.

1. `.cursor/rules/medication-companion.mdc` — spec first, always
2. `data/india_brands.csv` — seed the drug name data
3. `tools/drug_lookup.py` — test with Azee, Augmentin, Pantocid DSR
4. `tools/combo_splitter.py` — test that Pantocid DSR → 2 components
5. `tools/guardrails.py` — test rejection of diagnostic questions and injection patterns
6. `memory/session_service.py` — local mode first, vertex mode behind env var
7. `memory/memory_service.py` — local mode first, vertex mode behind env var
8. `agents/agent1_reader.py` — test with a clear and a blurry prescription image
9. `agents/agent2_resolver.py` — test that NEW/EXISTING tagging works with a seeded memory
10. `agents/agent3_safety.py` — test with a known interacting pair (e.g. warfarin + aspirin)
11. `agents/agent4_education.py` — test that output tone changes with HIGH vs LOW severity input
12. `main.py` — wire agents 1–4, test full pipeline locally
13. `tools/tts.py` — test GCP TTS call, stub in local mode
14. `agents/agent5_localisation.py` — test Hindi translation output
15. `a2a_server.py` — test Agent Card endpoint + A2A task endpoint
16. `evaluation/llm_judge.py` — test scoring on a known good and known bad output
17. Firebase Auth middleware in `main.py` — test 401 on missing token
18. `deploy/deploy.sh` — deploy to GCP, smoke test both Cloud Run URLs
19. Flutter frontend — build screens in order: Login → Home → Upload → Result
20. End-to-end test: real prescription photo → deployed Cloud Run → Flutter result screen → audio playback
