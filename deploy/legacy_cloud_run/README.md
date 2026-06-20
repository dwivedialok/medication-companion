# Legacy Cloud Run artifacts

This directory archives the FastAPI-based Cloud Run deployment that preceded
the Vertex AI Agent Runtime migration (Phase 0 of the Day 4/5 capstone plan).

Kept as a reference for the capstone writeup and as a rollback path. None of
these files are imported by the running agent; the active deployment is
defined by [`backend/agent_runtime_app.py`](../../backend/agent_runtime_app.py)
and the Terraform under [`deployment/`](../../deployment).

| File | Replaced by |
|------|-------------|
| `main.py` | `backend/agent_runtime_app.py` (`AgentEngineApp` wraps `App`) |
| `a2a_server.py` | Agent 5 inlined into `root_agent` SequentialAgent |
| `Dockerfile`, `Dockerfile.a2a` | Source-based Agent Runtime deploy (no container) |
| `requirements.txt` | `pyproject.toml` + `uv.lock` at repo root |
| `session_service.py` | `VertexAiSessionService` (managed by Agent Runtime) |

To restore the Cloud Run path: revert this PR or
`agents-cli scaffold enhance . --deployment-target cloud_run --agent-directory backend --yes`.
