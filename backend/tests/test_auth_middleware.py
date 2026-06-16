"""
Unit tests for the Firebase Auth middleware logic.

Uses a minimal FastAPI test app that mirrors the auth logic from main.py,
avoiding the need to import the full agent pipeline (which requires Gemini credentials).
"""
import os
from unittest.mock import patch

import pytest
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("ENVIRONMENT", "local")
os.environ.setdefault("DEV_PATIENT_ID", "test-patient-001")
os.environ.setdefault("MEMORY_BACKEND", "local")

_PUBLIC_PATHS = {"/health"}


def _make_auth_app(environment: str, dev_patient_id: str) -> FastAPI:
    """Minimal FastAPI app with the same auth middleware logic as main.py."""
    test_app = FastAPI()

    @test_app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        if environment == "local" and dev_patient_id:
            request.state.patient_id = dev_patient_id
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "unauthorized"},
            )

        token = auth_header.removeprefix("Bearer ").strip()
        try:
            import firebase_admin
            from firebase_admin import auth as fb_auth

            if not firebase_admin._apps:
                firebase_admin.initialize_app()

            decoded = fb_auth.verify_id_token(token)
            request.state.patient_id = decoded["uid"]
        except Exception:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "unauthorized"},
            )

        return await call_next(request)

    @test_app.get("/health")
    async def health():
        return {"status": "ok"}

    @test_app.get("/protected")
    async def protected(request: Request):
        return {"patient_id": request.state.patient_id}

    return test_app


# ── Public endpoint bypasses auth ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_bypasses_auth():
    app = _make_auth_app(environment="production", dev_patient_id="")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200


# ── Local mode bypass ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dev_patient_id_bypass_sets_patient_id():
    app = _make_auth_app(environment="local", dev_patient_id="test-patient-001")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/protected")
    assert resp.status_code == 200
    assert resp.json()["patient_id"] == "test-patient-001"


@pytest.mark.asyncio
async def test_local_mode_no_token_needed():
    app = _make_auth_app(environment="local", dev_patient_id="dev-user")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/protected")  # no Authorization header
    assert resp.status_code == 200


# ── Production mode: missing token ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_missing_token_returns_401():
    app = _make_auth_app(environment="production", dev_patient_id="")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/protected")
    assert resp.status_code == 401
    assert resp.json()["error"] == "unauthorized"


@pytest.mark.asyncio
async def test_malformed_bearer_returns_401():
    app = _make_auth_app(environment="production", dev_patient_id="")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/protected", headers={"Authorization": "Basic abc123"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_bearer_without_token_returns_401():
    app = _make_auth_app(environment="production", dev_patient_id="")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/protected", headers={"Authorization": "Bearer "})
    assert resp.status_code == 401


# ── Production mode: invalid token ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_invalid_firebase_token_returns_401():
    app = _make_auth_app(environment="production", dev_patient_id="")
    with patch("firebase_admin.auth.verify_id_token", side_effect=Exception("Invalid token")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/protected",
                headers={"Authorization": "Bearer bad.token.value"},
            )
    assert resp.status_code == 401
    assert resp.json()["error"] == "unauthorized"


# ── Valid token sets patient_id ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_valid_token_sets_patient_id():
    app = _make_auth_app(environment="production", dev_patient_id="")
    with patch(
        "firebase_admin.auth.verify_id_token",
        return_value={"uid": "firebase-uid-123"},
    ):
        with patch("firebase_admin._apps", {"default": object()}):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(
                    "/protected",
                    headers={"Authorization": "Bearer valid.token.here"},
                )
    assert resp.status_code == 200
    assert resp.json()["patient_id"] == "firebase-uid-123"
