# GEMINI.md — Model overrides for Medication Companion agents

Per-agent Gemini configuration for this directory. Global hard rules live in
[AGENTS.md](../../AGENTS.md) and [.cursor/rules/medication-companion.mdc](../../.cursor/rules/medication-companion.mdc).
This file adds **model-level** guidance only.

## Endpoint

All agents use `GlobalGemini` from [backend/llm_models.py](../llm_models.py), which pins
the Vertex AI client to `locations/global`. Project region (`GOOGLE_CLOUD_LOCATION=us-central1`)
applies to Agent Runtime, GCS, and Memory Bank — not to Gemini model calls.

## Model registry

Resolved via env vars (see `.env.example`). Per-agent override wins over global `GEMINI_MODEL`.

| Agent | Env key | Default | Rationale |
|-------|---------|---------|-----------|
| prescription_reader | `PRESCRIPTION_IMAGE_READER_LLM_MODEL` | gemini-3.1-flash-lite | Vision OCR; needs low latency |
| medication_resolver | `DRUG_NAME_RESOLVER_LLM_MODEL` | gemini-3.1-flash-lite | Tool-calling for lookup + FDC split |
| medication_safety | `MEDICATION_SAFETY_LLM_MODEL` | gemini-3.1-flash-lite | Structured JSON; pair enumeration |
| patient_education | `PATIENT_EDUCATION_LLM_MODEL` | gemini-3.1-flash-lite | Plain-language generation |
| localisation_audio | `LOCALISATION_AUDIO_LLM_MODEL` | gemini-3.1-flash-lite | Translation fidelity + TTS tool call |
| LLM-as-Judge (eval) | `LLM_JUDGE_MODEL` | gemini-3.1-flash-lite | Async quality scoring |

## Generation parameters

ADK `LlmAgent` uses framework defaults unless overridden on the agent factory. For this
project:

- **Structured output agents (A1–A5):** rely on `output_schema` Pydantic models — do not
  add free-form prose instructions that compete with the schema.
- **Temperature:** keep default (low) for resolver and safety agents to reduce
  hallucinated drug names. Education and localisation may use slightly higher temperature
  only if eval scores regress — change one agent at a time and re-run `pytest tests/unit`.
- **Safety settings:** use ADK/Gemini defaults; do not disable safety filters for
  prescription images. Gate 1 and the policy server (Step 3) handle domain-specific refusal.

## Vision (Agent 1)

- Input arrives as `gs://` URI (production) or inline bytes (local runner).
- Confidence threshold is **0.75** — defined in code, not overridden here.
- Planned: `image_classification` enum for policy-server structural gate (Step 3).

## Tool-calling agents (A2, A3, A5)

- Agent 2 must call `drug_lookup` before guessing; tag `UNRESOLVED` on miss.
- Agent 3 must call `interaction_lookup` for every pair before pharmacological fallback.
- Agent 5 must call `text_to_speech` once per request; never invent audio URLs.

## What not to change here

- Severity vocabulary (`HIGH` | `MODERATE` | `LOW` | `INFO` | `NONE`) — project-wide constant.
- Mandatory disclaimer wording — enforced in agent instructions and guardrails.
- Switching to raw `google.genai` calls — always use `google.adk.agents.LlmAgent`.
