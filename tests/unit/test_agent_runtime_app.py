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


def test_global_gemini_uses_global_endpoint(monkeypatch):
    """GlobalGemini.api_client must pin Vertex to locations/global.

    Constructing google.genai.Client(vertexai=True) loads ADC when project is
    unset — mock Client so this stays an offline unit test.
    """
    from backend.llm_models import GlobalGemini

    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "ci-test-project")
    fake_client = MagicMock()
    fake_client._api_client.vertexai = True
    fake_client._api_client.location = "global"

    with patch("backend.llm_models.Client", return_value=fake_client) as mock_client:
        model = GlobalGemini(model="gemini-3.1-flash-lite")
        client = model.api_client

    mock_client.assert_called_once_with(
        vertexai=True, location="global", project="ci-test-project"
    )
    assert client._api_client.vertexai is True
    assert client._api_client.location == "global"
