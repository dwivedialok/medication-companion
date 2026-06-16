"""Tests for backend/llm_models.py — central model registry."""
from llm_models import (
    DEFAULT_GEMINI_MODEL,
    DRUG_NAME_RESOLVER_LLM,
    LLM_JUDGE_MODEL,
    LOCALISATION_AUDIO_LLM,
    MEDICATION_SAFETY_LLM,
    PATIENT_EDUCATION_LLM,
    PRESCRIPTION_IMAGE_READER_LLM,
    agent_model_registry,
)


def test_default_model_is_gemini_3_5_flash():
    assert DEFAULT_GEMINI_MODEL == "gemini-3.5-flash"


def test_all_agent_constants_use_default_when_no_env(monkeypatch):
    for key in (
        "GEMINI_MODEL",
        "PRESCRIPTION_IMAGE_READER_LLM_MODEL",
        "DRUG_NAME_RESOLVER_LLM_MODEL",
        "MEDICATION_SAFETY_LLM_MODEL",
        "PATIENT_EDUCATION_LLM_MODEL",
        "LOCALISATION_AUDIO_LLM_MODEL",
        "LLM_JUDGE_MODEL",
    ):
        monkeypatch.delenv(key, raising=False)

    import importlib
    import llm_models

    importlib.reload(llm_models)

    assert llm_models.PRESCRIPTION_IMAGE_READER_LLM == "gemini-3.5-flash"
    assert llm_models.DRUG_NAME_RESOLVER_LLM == "gemini-3.5-flash"
    assert llm_models.MEDICATION_SAFETY_LLM == "gemini-3.5-flash"
    assert llm_models.PATIENT_EDUCATION_LLM == "gemini-3.5-flash"
    assert llm_models.LOCALISATION_AUDIO_LLM == "gemini-3.5-flash"
    assert llm_models.LLM_JUDGE_MODEL == "gemini-3.5-flash"


def test_agent_model_registry_has_five_agents():
    registry = agent_model_registry()
    assert set(registry) == {
        "prescription_reader",
        "medication_resolver",
        "medication_safety",
        "patient_education",
        "localisation_audio",
    }
    assert all(isinstance(v, str) and v for v in registry.values())
