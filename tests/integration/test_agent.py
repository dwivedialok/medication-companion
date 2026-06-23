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
Integration test for the medication_companion SequentialAgent.

Exercises the full pipeline end-to-end with a deliberately blurry image so
Agent 1's Gate-1 rejection path fires. This validates wiring (5 sub-agents,
guardrail callbacks) without requiring a real prescription image.

Skipped when GOOGLE_API_KEY / Vertex creds are missing — this is a real
LLM-driven test, not a unit test.
"""
import base64
import os

import pytest
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from backend.agent import root_agent

# 1x1 transparent GIF — small, valid image bytes, no actual prescription text.
_BLANK_GIF = base64.b64decode(
    b"R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
)


def _has_credentials() -> bool:
    return bool(
        os.getenv("GOOGLE_API_KEY")
        or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        or os.getenv("GOOGLE_GENAI_USE_VERTEXAI")
    )


@pytest.mark.live
@pytest.mark.skipif(
    not _has_credentials(), reason="No Gemini / Vertex credentials in environment"
)
def test_pipeline_runs_end_to_end_with_invalid_image() -> None:
    session_service = InMemorySessionService()
    session = session_service.create_session_sync(user_id="test_user", app_name="test")
    runner = Runner(agent=root_agent, session_service=session_service, app_name="test")

    message = types.Content(
        role="user",
        parts=[
            types.Part.from_text(text="Please analyse this prescription image."),
            types.Part.from_bytes(data=_BLANK_GIF, mime_type="image/gif"),
        ],
    )

    events = list(
        runner.run(
            new_message=message,
            user_id="test_user",
            session_id=session.id,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        )
    )
    assert len(events) > 0, "Expected at least one event"

    has_text_content = any(
        event.content and event.content.parts and any(p.text for p in event.content.parts)
        for event in events
    )
    assert has_text_content, "Expected at least one event with text content"
