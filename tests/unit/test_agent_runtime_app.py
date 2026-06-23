"""Unit tests for AgentEngineApp startup and Gemini endpoint pinning."""
import os
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

from backend.agent_runtime_app import AgentEngineApp


def _run_set_up(app: AgentEngineApp) -> None:
    with ExitStack() as stack:
        stack.enter_context(patch("backend.agent_runtime_app.vertexai.init"))
        stack.enter_context(patch("backend.agent_runtime_app.setup_telemetry"))
        stack.enter_context(patch("vertexai.agent_engines.templates.adk.AdkApp.set_up"))
        stack.enter_context(patch("backend.agent_runtime_app.google_cloud_logging.Client"))
        app.set_up()


def test_set_up_does_not_mutate_cloud_location(monkeypatch):
    """GOOGLE_CLOUD_LOCATION must remain the project's regional setting.

    Gemini endpoint is pinned per-model via GlobalGemini in llm_models.py, so
    set_up() should NOT override the project-wide GOOGLE_CLOUD_LOCATION.
    """
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-central1")

    app = AgentEngineApp(app=MagicMock())
    _run_set_up(app)

    assert os.environ["GOOGLE_CLOUD_LOCATION"] == "us-central1"


def test_global_gemini_uses_global_endpoint():
    """GlobalGemini.api_client must point at locations/global regardless of env."""
    from backend.llm_models import GlobalGemini

    model = GlobalGemini(model="gemini-3.1-flash-lite")
    client = model.api_client
    assert client._api_client.vertexai is True
    assert client._api_client.location == "global"
