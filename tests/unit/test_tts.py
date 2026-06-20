"""
Unit tests for backend/tools/tts.py.
All tests run in local mode — no GCP credentials required.
"""
import os

import pytest

os.environ.setdefault("ENVIRONMENT", "local")


# ── Tool wrapping ─────────────────────────────────────────────────────────────

def test_tts_tool_is_function_tool():
    from google.adk.tools import FunctionTool
    from tools.tts import tts_tool

    assert isinstance(tts_tool, FunctionTool)


# ── Local stub behaviour ──────────────────────────────────────────────────────

def test_stub_returns_audio_url(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "local")
    from tools.tts import text_to_speech

    result = text_to_speech("Hello", "hi-IN")
    assert "audio_url" in result
    assert result["audio_url"]


def test_stub_returns_duration_int(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "local")
    from tools.tts import text_to_speech

    result = text_to_speech("Hello", "hi-IN")
    assert isinstance(result["duration_seconds"], int)


def test_stub_does_not_call_gcp(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "local")
    # If GCP were called it would fail — confirming no network access
    from tools.tts import text_to_speech

    result = text_to_speech("Long explanation text for a prescription.", "en-IN")
    assert result["audio_url"] != ""


def test_stub_url_is_constant(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "local")
    from tools.tts import _STUB_AUDIO_URL, text_to_speech

    result = text_to_speech("Any text", "hi-IN")
    assert result["audio_url"] == _STUB_AUDIO_URL


# ── All supported language codes ──────────────────────────────────────────────

@pytest.mark.parametrize("language_code", ["hi-IN", "ta-IN", "te-IN", "bn-IN", "en-IN"])
def test_all_language_codes_accepted(language_code, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "local")
    from tools.tts import text_to_speech

    result = text_to_speech("Sample explanation.", language_code)
    assert result["audio_url"]
    assert "duration_seconds" in result


# ── Return type ───────────────────────────────────────────────────────────────

def test_returns_dict(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "local")
    from tools.tts import text_to_speech

    result = text_to_speech("test", "en-IN")
    assert isinstance(result, dict)


def test_required_keys_present(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "local")
    from tools.tts import text_to_speech

    result = text_to_speech("test", "en-IN")
    assert "audio_url" in result
    assert "duration_seconds" in result
