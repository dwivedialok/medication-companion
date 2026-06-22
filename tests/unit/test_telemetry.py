"""Unit tests for backend/app_utils/telemetry.py."""
from __future__ import annotations

import logging
import os

import pytest

from app_utils.telemetry import resolve_capture_mode, setup_telemetry


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("EVENT_ONLY", "EVENT_ONLY"),
        ("event_only", "EVENT_ONLY"),
        ("NO_CONTENT", "NO_CONTENT"),
        ("false", None),
        ("", None),
        ("true", "NO_CONTENT"),
        ("bogus", None),
    ],
)
def test_resolve_capture_mode(raw: str, expected: str | None):
    assert resolve_capture_mode(raw) == expected


def test_setup_telemetry_respects_event_only(monkeypatch):
    monkeypatch.setenv("LOGS_BUCKET_NAME", "medication-companion-dev-medication-companion-logs")
    monkeypatch.setenv(
        "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "EVENT_ONLY"
    )
    for key in (
        "OTEL_INSTRUMENTATION_GENAI_UPLOAD_FORMAT",
        "OTEL_INSTRUMENTATION_GENAI_COMPLETION_HOOK",
        "OTEL_INSTRUMENTATION_GENAI_UPLOAD_BASE_PATH",
    ):
        monkeypatch.delenv(key, raising=False)

    setup_telemetry()

    assert (
        os.environ.get("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT")
        == "EVENT_ONLY"
    )
    assert "completions" in os.environ.get(
        "OTEL_INSTRUMENTATION_GENAI_UPLOAD_BASE_PATH", ""
    )


def test_setup_telemetry_disabled_without_bucket(monkeypatch):
    monkeypatch.delenv("LOGS_BUCKET_NAME", raising=False)
    monkeypatch.setenv(
        "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "EVENT_ONLY"
    )

    setup_telemetry()

    assert os.environ.get("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT") == "EVENT_ONLY"


def test_setup_telemetry_warns_on_unknown_mode(
    monkeypatch, caplog: pytest.LogCaptureFixture
):
    monkeypatch.setenv("LOGS_BUCKET_NAME", "test-logs")
    monkeypatch.setenv("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "nope")

    with caplog.at_level(logging.WARNING):
        setup_telemetry()

    assert "Unknown OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT" in caplog.text
