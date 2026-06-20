"""
backend/llm_models.py
Central registry of Gemini model IDs for Medication Companion.

Resolution order for each constant:
  1. Per-agent env override (e.g. PRESCRIPTION_IMAGE_READER_LLM_MODEL)
  2. Global GEMINI_MODEL in .env
  3. DEFAULT_GEMINI_MODEL below

Agent mapping:
  PRESCRIPTION_IMAGE_READER_LLM  → Agent 1 (prescription_reader)
  DRUG_NAME_RESOLVER_LLM         → Agent 2 (medication_resolver)
  MEDICATION_SAFETY_LLM          → Agent 3 (medication_safety)
  PATIENT_EDUCATION_LLM          → Agent 4 (patient_education)
  LOCALISATION_AUDIO_LLM         → Agent 5 (localisation_audio)
  LLM_JUDGE_MODEL                → evaluation/llm_judge.py (async quality scoring)
"""
import os

DEFAULT_GEMINI_MODEL = "gemini-3.1-flash-lite"


def _resolve_model(per_agent_env_key: str) -> str:
    return (
        os.getenv(per_agent_env_key)
        or os.getenv("GEMINI_MODEL")
        or DEFAULT_GEMINI_MODEL
    )


# Agent 1 — vision OCR + Gate 1 confidence check
PRESCRIPTION_IMAGE_READER_LLM = _resolve_model("PRESCRIPTION_IMAGE_READER_LLM_MODEL")

# Agent 2 — brand → generic, FDC split (FunctionTools)
DRUG_NAME_RESOLVER_LLM = _resolve_model("DRUG_NAME_RESOLVER_LLM_MODEL")

# Agent 3 — cross-visit interaction check (memory)
MEDICATION_SAFETY_LLM = _resolve_model("MEDICATION_SAFETY_LLM_MODEL")

# Agent 4 — plain-language patient explanation
PATIENT_EDUCATION_LLM = _resolve_model("PATIENT_EDUCATION_LLM_MODEL")

# Agent 5 — translation + TTS (A2A service)
LOCALISATION_AUDIO_LLM = _resolve_model("LOCALISATION_AUDIO_LLM_MODEL")

# Day 4 eval — async LLM-as-Judge (safety + clarity scores)
LLM_JUDGE_MODEL = _resolve_model("LLM_JUDGE_MODEL")


def agent_model_registry() -> dict[str, str]:
    """Agent name → model ID, for eval logging and debugging."""
    return {
        "prescription_reader": PRESCRIPTION_IMAGE_READER_LLM,
        "medication_resolver": DRUG_NAME_RESOLVER_LLM,
        "medication_safety": MEDICATION_SAFETY_LLM,
        "patient_education": PATIENT_EDUCATION_LLM,
        "localisation_audio": LOCALISATION_AUDIO_LLM,
    }
