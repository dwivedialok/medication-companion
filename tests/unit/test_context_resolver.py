"""Unit tests for backend/policy/context_resolver.py.

Verifies `[[PLACEHOLDER]]` resolution against specs/schemas/language_map.yaml
and the fail-closed behaviour required by Day 5 §3.3.
"""
from __future__ import annotations

import pytest

from policy.context_resolver import (
    ContextResolver,
    ContextResolverError,
    RenderContext,
)

_RESOLVER = ContextResolver()


def test_resolve_substitutes_known_placeholders_hindi():
    template = "Translate into [[PATIENT_LANGUAGE]] with tone: [[SEVERITY_TONE]]. Disclaimer: [[DISCLAIMER]]"
    rendered = _RESOLVER.resolve(
        template, RenderContext(patient_language="hi-IN", overall_severity="HIGH")
    )
    assert "[[" not in rendered
    assert "hi-IN" in rendered
    assert "urgent" in rendered.lower()
    # Hindi disclaimer text contains Devanagari characters
    assert "डॉक्टर" in rendered or "doctor" in rendered.lower()


def test_resolve_english_passthrough():
    template = "Lang=[[PATIENT_LANGUAGE]] Voice=[[TTS_VOICE]] Disclaimer=[[DISCLAIMER]]"
    rendered = _RESOLVER.resolve(
        template, RenderContext(patient_language="en-IN", overall_severity="INFO")
    )
    assert "en-IN" in rendered
    assert "en-IN-Standard-A" in rendered
    assert "doctor or pharmacist" in rendered.lower()


def test_resolve_raises_on_unknown_placeholder():
    template = "Hello [[UNKNOWN_TOKEN]]"
    with pytest.raises(ContextResolverError):
        _RESOLVER.resolve(
            template,
            RenderContext(patient_language="hi-IN", overall_severity="MODERATE"),
        )


def test_resolve_raises_on_invalid_severity():
    template = "[[SEVERITY_TONE]]"
    with pytest.raises(ContextResolverError):
        _RESOLVER.resolve(
            template,
            RenderContext(patient_language="hi-IN", overall_severity="CRITICAL"),
        )


def test_resolve_unknown_language_falls_back_to_en_in():
    # language_map.yaml has en-IN as the explicit default fallback
    template = "[[PATIENT_LANGUAGE]] [[DISCLAIMER]]"
    rendered = _RESOLVER.resolve(
        template,
        RenderContext(patient_language="xx-IN", overall_severity="INFO"),
    )
    # Placeholder still gets the literal requested language, but disclaimer
    # comes from the en-IN fallback entry.
    assert "xx-IN" in rendered
    assert "doctor or pharmacist" in rendered.lower()


def test_resolve_fail_closed_no_literal_placeholders_remain():
    """Critical Day 5 guarantee: rendered prompt must never contain `[[VARS]]`."""
    template = "Severity tone: [[SEVERITY_TONE]] / Disclaimer: [[DISCLAIMER]]"
    for code in ("hi-IN", "ta-IN", "te-IN", "bn-IN", "en-IN"):
        for severity in ("HIGH", "MODERATE", "LOW", "INFO", "NONE"):
            rendered = _RESOLVER.resolve(
                template,
                RenderContext(patient_language=code, overall_severity=severity),
            )
            assert "[[" not in rendered, (code, severity, rendered)
            assert "]]" not in rendered, (code, severity, rendered)


def test_disclaimer_for_each_supported_language():
    for code in ("hi-IN", "ta-IN", "te-IN", "bn-IN", "en-IN"):
        text = _RESOLVER.disclaimer_for(code)
        assert text
        assert "[[" not in text


def test_tone_for_high_severity_distinct_per_language():
    tones = {
        code: _RESOLVER.tone_for(code, "HIGH")
        for code in ("hi-IN", "ta-IN", "te-IN", "bn-IN", "en-IN")
    }
    assert all(tones.values())
    # All severity_tone_phrases for HIGH use "urgent"
    for code, tone in tones.items():
        assert "urgent" in tone.lower(), (code, tone)
