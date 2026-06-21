# Specs — Medication Companion

Behavioral specifications for the multi-agent prescription pipeline. These files are the
**permanent source of truth** (Day 5 SDD): code in `backend/` is generated and maintained
to satisfy these specs.

## Layout

| File | Purpose |
|------|---------|
| [pipeline.feature](pipeline.feature) | Happy-path and edge-case pipeline scenarios |
| [safety_refusal.feature](safety_refusal.feature) | Image intake + output policy gates (v1) |
| [future/qa_extension.feature](future/qa_extension.feature) | Deferred chat Q&A scenarios (`FEATURE_QA_ENABLED`) |
| [agent_boundaries.yaml](agent_boundaries.yaml) | Per-agent inputs, outputs, forbidden actions |
| [schemas/medication_history.yaml](schemas/medication_history.yaml) | Cross-visit memory record shape |
| [schemas/interaction_matrix.yaml](schemas/interaction_matrix.yaml) | `interaction_lookup` tool contract |
| [schemas/language_map.yaml](schemas/language_map.yaml) | Language codes, TTS voices, tone phrases |
| [schemas/evaluation_metrics.yaml](schemas/evaluation_metrics.yaml) | LLM-as-Judge dimensions for generative outputs |

## Deterministic vs generative verification

Some spec steps describe **behavioral intent** for LLM-generated text (translation fidelity,
tone, explanation clarity). Those are **not** checked with binary pytest assertions.

| Outcome type | How it is verified |
|--------------|-------------------|
| Gate 1 status, UNRESOLVED tags, interaction severity | Unit/integration tests (exact values) |
| Disclaimer present, language_code, audio_url shape | Unit tests (structural checks) |
| Translation fidelity, tone, intent satisfaction | **LLM-as-Judge** async scores — see [schemas/evaluation_metrics.yaml](schemas/evaluation_metrics.yaml) |
| Policy semantic deny | Policy server + red-team eval (Step 4+) |

Implemented judge dimensions today: `drug_safety_score`, `patient_clarity_score`
(`backend/evaluation/llm_judge.py`). Planned for capstone Step 5:
`translation_accuracy_score`, `tone_calibration_score`, `intent_satisfaction_score`,
`trajectory_quality_score`.

## Instruction hierarchy (Day 5)

```
AGENTS.md              → global project DNA (hard rules)
backend/agents/GEMINI.md → model-specific overrides
specs/                 → static behavioral blueprints (this folder)
.agent/skills/         → reusable feature workflows
docs/forensic_prompts.md → evidence-driven bug-fix templates
```

## Spec → test mapping

| Spec scenario | Test coverage |
|---------------|---------------|
| Gate 1 reject (unreadable image) | `tests/integration/test_agent.py` (pipeline halt) |
| Drug lookup tiers + UNRESOLVED | `tests/unit/test_drug_lookup.py`, `tests/unit/test_drug_lookup_eval.py` |
| Interaction lookup severity | `tests/unit/test_interaction_lookup.py` |
| Cross-visit memory read/write | `tests/unit/test_patient_memory.py`, `tests/unit/test_memory_services.py` |
| Input/output guardrails | `tests/unit/test_guardrails.py` |
| Auth broker JWT + upload flow | `tests/unit/test_auth_broker.py`, `tests/unit/test_agent_client.py` |
| Pipeline output assembly | `tests/unit/test_pipeline_output.py` |
| TTS voice map | `tests/unit/test_tts.py` |
| Localisation fidelity + tone | **LLM-as-Judge** — `tests/eval/eval_config.yaml` (`translation_accuracy_score` planned Step 5) |
| Non-prescription / overlay injection deny | **Planned** — `tests/unit/test_policy_server.py` (Step 3) |
| Semantic output deny (OTC, diagnostic) | **Planned** — `tests/unit/test_policy_server.py` (Step 3) |
| ContextResolver placeholders | **Planned** — `tests/unit/test_context_resolver.py` (Step 3) |
| Q&A input gate | **Deferred** — skipped while `FEATURE_QA_ENABLED=false` |

Run the full suite from the repo root:

```bash
uv run pytest tests/unit tests/integration
```

## Implementation status

| Area | Spec | Code status |
|------|------|-------------|
| SequentialAgent A1–A5 | pipeline.feature | Implemented (`backend/agent.py`) |
| Gate 1 confidence reject | pipeline.feature | Implemented (Agent 1 `ReaderOutput`) |
| `image_classification` enum | safety_refusal.feature | **Step 3** — not yet in Agent 1 schema |
| Policy server gates | safety_refusal.feature | **Step 3** — `backend/policy/` not yet created |
| ContextResolver `[[VARS]]` | language_map.yaml | **Step 3** — Agent 5 uses inline instruction today |
| Q&A chat safety | future/qa_extension.feature | Deferred post-capstone |

When implementing Step 3, update this README's status table and add the linked tests
before merging policy-server code.
