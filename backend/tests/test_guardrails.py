"""
Unit tests for backend/tools/guardrails.py.
Run from backend/ dir: pytest tests/test_guardrails.py -v
"""
import pytest
from pydantic import BaseModel

from tools.guardrails import (
    REQUIRED_DISCLAIMER,
    _sanitize_output,
    _sanitize_text,
)


class SampleOutput(BaseModel):
    summary: str
    disclaimer: str = ""


def test_sanitize_text_strips_diagnostic_language():
    text = "You have a serious interaction. Please review."
    result = _sanitize_text(text, session_id="test-session")
    assert "you have" not in result.lower()
    assert "[removed]" in result


def test_sanitize_text_injects_disclaimer():
    result = _sanitize_text("Some safe summary.", session_id="test-session")
    assert REQUIRED_DISCLAIMER in result


def test_sanitize_output_updates_pydantic_model():
    output = SampleOutput(
        summary="You have a potential issue with this medicine.",
        disclaimer="Short disclaimer only.",
    )
    sanitized = _sanitize_output(output, session_id="test-session")
    assert isinstance(sanitized, SampleOutput)
    assert "you have" not in sanitized.summary.lower()
    assert REQUIRED_DISCLAIMER in sanitized.summary
    assert REQUIRED_DISCLAIMER in sanitized.disclaimer


@pytest.mark.asyncio
async def test_output_guardrail_callback_writes_sanitized_output():
    from tools.guardrails import output_guardrail_callback

    class FakeSession:
        id = "sess-1"

    class FakeCallbackContext:
        def __init__(self, output):
            self.output = output
            self.session = FakeSession()

    original = SampleOutput(
        summary="You have an interaction to discuss.",
        disclaimer="Info only.",
    )
    ctx = FakeCallbackContext(original)
    await output_guardrail_callback(ctx)
    assert "you have" not in ctx.output.summary.lower()
    assert REQUIRED_DISCLAIMER in ctx.output.summary
