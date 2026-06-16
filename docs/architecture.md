# Architecture — Medication Companion

## System overview

Medication Companion is a **multi-agent pipeline** built with Google ADK + Gemini.
Each agent has a single, bounded responsibility. Agents communicate via structured
Pydantic models through ADK session state — never plain dicts, never free text between agents.

---

## Agent pipeline

```
Image upload
    │
    ▼
[Input Guardrail] ──(reject)──► HTTP 400 to patient
    │
    ▼
Agent 1: Prescription Reader
  • Gemini Vision extracts drug names
  • Assigns confidence score per name
  • Gate 1: any confidence < 0.75 → Gate1Reject → HTTP 422 to patient
    │
    ▼
Agent 2: Medication Resolver
  • Calls drug_lookup FunctionTool (RxNav API → India CSV fallback)
  • Calls combo_splitter FunctionTool for FDC products
  • Tags each drug NEW or EXISTING (checks Vertex AI memory)
    │
    ▼
Agent 3: Reconciliation & Safety
  • Reads current visit drugs from session state (Agent 2 output)
  • Reads prior visit drugs from Vertex AI MemoryBankService
  • LLM checks interactions: current × current AND current × prior
  • Outputs severity-tagged interaction list
    │
    ▼
Agent 4: Patient Education
  • Generates plain-language explanation calibrated to severity
  • Builds drug cards, interaction cards, doctor questions
  • Mandatory disclaimer injected
  • Triggers LLM-as-Judge async (non-blocking)
  • Triggers memory write (resolved drugs → VertexAiMemoryBankService)
    │
    ▼
[Output Guardrail] ──(sanitise)──► strips diagnostic language, injects disclaimer
    │
    ▼
  A2A call to Agent 5
    │
    ▼
Agent 5: Localisation + Audio (separate Cloud Run service)
  • Translates to patient language (hi-IN, ta-IN, te-IN, bn-IN, en-IN)
  • Calls GCP Text-to-Speech via FunctionTool
  • Uploads MP3 to Cloud Storage
  • Returns signed URL (24h expiry)
    │
    ▼
JSON response to Flutter PWA
```

---

## Session state schema

```python
class SessionState(BaseModel):
    session_id: str
    patient_id: str              # Firebase UID — never trust client body
    visit_timestamp: datetime
    
    # Agent 1 output
    extracted_drugs: list[ExtractedDrug]
    gate1_passed: bool
    
    # Agent 2 output
    resolved_drugs: list[ResolvedDrug]
    
    # Agent 3 output
    interactions: list[Interaction]
    overall_severity: str
    
    # Agent 4 output
    education_output: EducationOutput
    
    # A2A response
    audio_url: str | None
    translated_text: str | None
```

---

## Memory architecture

| Type | Service | Scope | What is stored |
|------|---------|-------|----------------|
| Short-term | `VertexAiSessionService` | Single pipeline run | Session state above |
| Long-term | `VertexAiMemoryBankService` | Cross-visit per patient | Resolved generic names + visit timestamp + severity summary |

Memory is keyed by `patient_id` (Firebase UID). Isolation between patients is enforced
at the service level — the memory service wrapper validates the patient_id matches
the verified JWT before any read or write.

**What is never stored in memory:** prescription images, clinical notes, diagnosis text,
raw LLM output, PII beyond patient_id.

---

## LLM cost discipline

LLM calls in this system:
- Agent 1: one vision call per run (image analysis)
- Agent 2: one call + 1-2 tool calls (deterministic tools reduce LLM load)
- Agent 3: one call (reads structured session state — no re-processing)
- Agent 4: one call (reads structured Agent 3 output)
- Agent 5: one translation call + one TTS tool call
- LLM-as-Judge: two calls async (non-blocking, post-response)

Total per run: ~7 LLM calls. Agent 2's deterministic tools (RxNav, combo_splitter)
avoid LLM calls for the resolution step.

---

## Observability

- **Cloud Trace**: each agent is an OpenTelemetry named span. Full waterfall (Agent 1 → Agent 5 via A2A) visible in Cloud Trace.
- **Structured logging**: `google.cloud.logging` JSON format on both services. Guardrail rejections, memory writes, and judge scores are all logged with session_id.
- **BigQuery audit**: `medication_companion.eval_log` captures LLM-as-Judge scores per run. `medication_companion.pipeline_audit` captures latency and severity per run.
- **Health endpoints**: `GET /health` on both Cloud Run services.

---

## Security model

- Both Cloud Run services: `--no-allow-unauthenticated`
- Firebase Auth JWT validated on every request at FastAPI middleware layer
- `patient_id` extracted from verified JWT — never from client request body
- Input guardrail: runs before Agent 1 on every request
- Output guardrail: runs after Agent 4 before response
- GCP IAM: service account with least-privilege roles (see `scripts/setup_gcp.sh`)
- Secrets in Secret Manager (not environment variables or images)

---

## Day-by-day course mapping

| Day | Concept | Architecture component |
|-----|---------|----------------------|
| 1 | Agents + Vibe Coding | Multi-agent pipeline; Gate 1 autonomous rejection; `.cursor/rules/` spec |
| 2 | Tools + Interoperability | `FunctionTool`s (RxNav, combo-splitter, TTS); Agent 5 as A2A service with Agent Card |
| 3 | Context Engineering (Memory) | `VertexAiSessionService`; `VertexAiMemoryBankService`; cross-visit interaction checking |
| 4 | Agent Quality | Input/output guardrail callbacks; LLM-as-Judge async scorer; BigQuery eval log |
| 5 | Spec-Driven Production | `.cursor/rules/medication-companion.mdc`; two Cloud Run services; Cloud Trace; `deploy.sh` |
