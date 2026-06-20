"""
backend/auth_broker/auth.py
Firebase JWT verification middleware for the token broker.
"""
from __future__ import annotations

import logging
import os

from fastapi import Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

PUBLIC_PATHS = {"/health", "/.well-known/agent.json"}


def _verify_firebase_token(token: str) -> str:
    import firebase_admin
    from firebase_admin import auth as fb_auth

    if not firebase_admin._apps:
        firebase_admin.initialize_app()

    decoded = fb_auth.verify_id_token(token)
    return decoded["uid"]


async def firebase_auth_middleware(request: Request, call_next):
    """Verify Firebase JWT and set request.state.patient_id from the UID."""
    if request.url.path in PUBLIC_PATHS:
        return await call_next(request)

    environment = os.getenv("ENVIRONMENT", "development")
    dev_patient_id = os.getenv("DEV_PATIENT_ID", "")

    if environment == "local" and dev_patient_id:
        request.state.patient_id = dev_patient_id
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "unauthorized", "message": "Missing Authorization header."},
        )

    token = auth_header.removeprefix("Bearer ").strip()
    try:
        request.state.patient_id = _verify_firebase_token(token)
    except Exception as exc:
        logger.warning("Firebase token verification failed: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "unauthorized", "message": "Invalid or expired token."},
        )

    return await call_next(request)
