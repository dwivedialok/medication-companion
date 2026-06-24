# Out of Scope — Medication Companion

This document states explicitly what is **not** in the current shipped build, and why each
exclusion is a deliberate engineering decision rather than an oversight. Behaviour that *is*
in scope is defined in [`specs/`](../specs/) (Gherkin scenarios + YAML schemas); see
[`specs/README.md`](../specs/README.md) for the spec → test mapping and implementation status.

---

## Explicitly excluded (product scope)

### Clinical interaction database
**Excluded:** No DrugBank, OpenFDA adverse event data, or structured pharmacological database.  
**Why:** The interaction matrix is a curated SQLite table built from public Kaggle sources plus
hand-maintained overrides. LLM pharmacological knowledge fills gaps at `INFO` severity only.
Integrating a clinical DB would add days of data-pipeline work with diminishing returns for
demonstrating agent architecture.

### Image pre-processing / OCR enhancement
**Excluded:** No deskewing, contrast enhancement, or binarisation pipeline before Agent 1.  
**Why:** Gemini Vision handles typical mobile prescription photos adequately. Gate 1 rejection
handles the failure case. A full OCR pipeline is a separate product concern.

### Full prescription history storage
**Excluded:** Memory stores resolved generic names, visit timestamp, and severity summary only —
not full prescription images or clinical notes.  
**Why:** Privacy by design. Agent 3 needs prior generics for cross-visit interaction checking;
storing images or clinical notes would turn this into a medical-records system.

### Pharmacy / dispensing integration
**Excluded:** No e-prescription, pharmacy API, or drug availability lookup.  
**Why:** Regulated commerce scope outside the agent-safety demonstration.

### Doctor-facing interface
**Excluded:** No dashboard, alert system, or report generation for healthcare providers.  
**Why:** The patient is the primary user. A clinician-facing product has different regulatory
and workflow requirements.

### Dose adjustment advice
**Excluded:** The system never suggests changing a dose, timing, or stopping a medication.  
**Why:** Hard safety boundary — dosing advice crosses into medical practice. Policy gates and
agent boundaries enforce this (`specs/agent_boundaries.yaml`).

### Refill reminders / adherence tracking
**Excluded:** No push notifications, refill scheduling, or adherence monitoring.  
**Why:** Requires persistent background services and notification infrastructure — separate from
the cross-visit safety-checking value proposition.

### Drug pricing / availability
**Excluded:** No pharmacy price lookup or drug availability by location.  
**Why:** Requires commercial data partnerships; not relevant to safety checking.

### Clinical trial matching
**Excluded:** No integration with ClinicalTrials.gov or trial eligibility checking.  
**Why:** Unrelated product surface; combining it with prescription safety would blur scope.

---

## Explicitly excluded (architecture & interoperability)

### Agent 5 as a separate A2A Cloud Run service
**Excluded in production:** Agent 5 (Localisation + Audio) does **not** run as an independent
service over the A2A protocol in the shipped build. All five agents execute **in-process** inside
one `SequentialAgent` on Vertex AI Agent Runtime (`deployment_metadata.json`: `is_a2a: false`).

**Why:** An A2A split was prototyped (separate Cloud Run service, Agent Card, `to_a2a()` handoff)
and is preserved under [`deploy/legacy_cloud_run/`](../deploy/legacy_cloud_run/) for reference.
Shipping in-process reduces deployment complexity, cold-start latency, and operational surface
while preserving the same patient-facing behaviour. A2A remains a **future extension** if
localisation/TTS needs independent scaling or third-party replacement.

**What still demonstrates Day 2 interoperability:** `FunctionTool`s with real external calls
(drug lookup, interaction lookup, TTS), structured tool outputs the LLM must not override, and
the archived A2A prototype in the repo.

### MCP tool servers
**Excluded:** No MCP server exposing tools to external clients.  
**Why:** Tools are ADK `FunctionTool`s registered on agents. MCP is not required for the
prescription pipeline demo.

---

## Specified but not yet implemented

The following appear in [`specs/`](../specs/) but are **deferred** or **partially implemented**
in the current build. They are out of scope for this release, not forgotten requirements.

| Spec area | Location | Status |
|-----------|----------|--------|
| Patient Q&A chat | `specs/future/qa_extension.feature` | Deferred — `FEATURE_QA_ENABLED=false` |
| Full policy-server gates (image classification enum, semantic deny, overlay injection) | `specs/safety_refusal.feature` | Partial — hybrid policy exists; full Step 3 scenarios not complete |
| ContextResolver `[[VARS]]` placeholders | `specs/schemas/language_map.yaml` | Deferred — Agent 5 uses inline instruction today |
| Per-component FDC interaction pairs | `specs/pipeline.feature` | Partial — Agent 3 pairs on combined `generic_name`; component expansion planned |
| Extended LLM-as-Judge dimensions | `specs/schemas/evaluation_metrics.yaml` | Partial — `drug_safety_score` + `patient_clarity_score` implemented; translation/tone/trajectory scores planned |
| LanceDB semantic drug resolver | `docs/drug_lookup_tool_v2.md` | Future — SQLite + fuzzy tiers ship today |

When any of the above ships, update [`specs/README.md`](../specs/README.md) and add tests
before merging.

---

## What the current build does demonstrate

- Five-agent pipeline with strict single-responsibility boundaries (`specs/agent_boundaries.yaml`)
- Real cross-visit memory (Vertex AI Memory Bank) enabling interaction checks across visits
- Deterministic interaction lookup via SQLite before LLM formatting
- `FunctionTool`s with external APIs (RxNav) and committed India drug index (`data/drugs.db`)
- Hybrid policy server on ADK callbacks (not baked into prompts alone)
- LLM-as-Judge async evaluation writing to BigQuery
- Spec-driven development — [`specs/`](../specs/) as source of truth; [`AGENTS.md`](../AGENTS.md) for hard rules
- Full GCP deployment: Vertex AI Agent Runtime, auth broker, Pub/Sub worker, Firebase Hosting
- Indian brand handling with curated CSV + Kaggle-built index and FDC decomposition
- Multilingual output (hi/ta/te/bn/en-IN) with GCP Text-to-Speech audio
