# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Integration tests for the AgentEngineApp wrapper deployed to Agent Runtime.

These tests require Gemini / Vertex credentials. They are skipped in CI runs
that don't provision them. The feedback test runs without credentials since
register_feedback() is a pure local log call.
"""
import logging
import os

import pytest
from google.adk.events.event import Event

from backend.agent_runtime_app import AgentEngineApp

# All tests in this module touch GCP (vertexai.init, Cloud Logging client).
pytestmark = pytest.mark.live


def _has_credentials() -> bool:
    return bool(
        os.getenv("GOOGLE_API_KEY")
        or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        or os.getenv("GOOGLE_GENAI_USE_VERTEXAI")
    )


@pytest.fixture
def agent_app(monkeypatch: pytest.MonkeyPatch) -> AgentEngineApp:
    """Fixture to create and set up AgentEngineApp instance"""
    monkeypatch.setenv("INTEGRATION_TEST", "TRUE")

    from backend.agent_runtime_app import agent_runtime

    agent_runtime.set_up()
    return agent_runtime


@pytest.mark.asyncio
@pytest.mark.skipif(
    not _has_credentials(), reason="No Gemini / Vertex credentials in environment"
)
async def test_agent_stream_query(agent_app: AgentEngineApp) -> None:
    """
    Smoke-tests the AgentEngineApp streaming path. We don't ship a real
    prescription image here — the medication pipeline will Gate-1 reject the
    text-only prompt, but the wrapper itself must still stream events.
    """
    message = "Please analyse this prescription image."
    events = []
    async for event in agent_app.async_stream_query(message=message, user_id="test"):
        events.append(event)
    assert len(events) > 0, "Expected at least one chunk in response"

    has_text_content = False
    for event in events:
        validated_event = Event.model_validate(event)
        content = validated_event.content
        if (
            content is not None
            and content.parts
            and any(part.text for part in content.parts)
        ):
            has_text_content = True
            break

    assert has_text_content, "Expected at least one event with text content"


def test_agent_feedback(agent_app: AgentEngineApp) -> None:
    """
    Integration test for the agent feedback functionality.
    Tests that feedback can be registered successfully.
    """
    feedback_data = {
        "score": 5,
        "text": "Great response!",
        "user_id": "test-user-456",
        "session_id": "test-session-456",
    }

    # Should not raise any exceptions
    agent_app.register_feedback(feedback_data)

    # Test invalid feedback
    with pytest.raises(ValueError):
        invalid_feedback = {
            "score": "invalid",  # Score must be numeric
            "text": "Bad feedback",
            "user_id": "test-user-789",
            "session_id": "test-session-789",
        }
        agent_app.register_feedback(invalid_feedback)

    logging.info("All assertions passed for agent feedback test")
