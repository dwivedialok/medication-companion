#!/usr/bin/env python3
"""
scripts/firebase_id_token.py
Obtain a Firebase ID token via Email/Password (Identity Toolkit REST API).

Use for A3 cloud smoke tests without opening browser DevTools.

Usage:
    export FIREBASE_TEST_EMAIL=you@example.com
    export FIREBASE_TEST_PASSWORD='your-password'
    uv run python scripts/firebase_id_token.py

    # Shell export (tokens expire ~1 hour):
    export FIREBASE_ID_TOKEN="$(uv run python scripts/firebase_id_token.py --print-token-only)"

    # One-liner with test_prescription.py:
    uv run python scripts/test_prescription.py "$RX_IMAGE" \\
      --url "https://medication-companion-dev.web.app" \\
      --token "$(uv run python scripts/firebase_id_token.py --print-token-only)"

Credentials: FIREBASE_TEST_EMAIL / FIREBASE_TEST_PASSWORD in repo-root `.env` (or exported env), or --email / --password.
Web API key: FIREBASE_WEB_API_KEY env, --api-key, or parsed from frontend/lib/firebase_options.dart
(when project_id matches).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import httpx
except ImportError:
    print("ERROR: httpx not installed. Run: uv sync", file=sys.stderr)
    sys.exit(1)

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")
load_dotenv(REPO_ROOT / ".env.local", override=False)
FIREBASE_OPTIONS = REPO_ROOT / "frontend/lib/firebase_options.dart"
IDENTITY_TOOLKIT = "https://identitytoolkit.googleapis.com/v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sign in with Firebase Email/Password and print an ID token."
    )
    parser.add_argument(
        "--project",
        default=None,
        help="Firebase/GCP project id (default: FIREBASE_PROJECT_ID or GOOGLE_CLOUD_PROJECT)",
    )
    parser.add_argument(
        "--email",
        default=None,
        help="Firebase user email (default: FIREBASE_TEST_EMAIL env)",
    )
    parser.add_argument(
        "--password",
        default=None,
        help="Firebase user password (default: FIREBASE_TEST_PASSWORD env)",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Firebase Web API key (default: FIREBASE_WEB_API_KEY or firebase_options.dart)",
    )
    parser.add_argument(
        "--print-token-only",
        action="store_true",
        help="Print only the ID token (no trailing newline metadata)",
    )
    parser.add_argument(
        "--sign-up",
        action="store_true",
        help="Create the user if sign-in fails with EMAIL_NOT_FOUND (dev smoke accounts only)",
    )
    return parser.parse_args()


def _env(name: str) -> str | None:
    import os

    value = os.getenv(name, "").strip()
    return value or None


def _read_api_key_from_flutter(project_id: str) -> str | None:
    if not FIREBASE_OPTIONS.is_file():
        return None
    text = FIREBASE_OPTIONS.read_text(encoding="utf-8")
    if f"projectId: '{project_id}'" not in text and f'projectId: "{project_id}"' not in text:
        return None
    match = re.search(r"apiKey:\s*'([^']+)'", text)
    if match:
        return match.group(1)
    match = re.search(r'apiKey:\s*"([^"]+)"', text)
    return match.group(1) if match else None


def _resolve_api_key(project_id: str, explicit: str | None) -> str:
    if explicit:
        return explicit
    from_env = _env("FIREBASE_WEB_API_KEY")
    if from_env:
        return from_env
    from_dart = _read_api_key_from_flutter(project_id)
    if from_dart:
        return from_dart
    print(
        "ERROR: Firebase Web API key not found.\n"
        "       Set FIREBASE_WEB_API_KEY, pass --api-key, or run flutterfire configure "
        f"for project {project_id}.",
        file=sys.stderr,
    )
    sys.exit(1)


def _identity_request(
    *,
    api_key: str,
    endpoint: str,
    payload: dict,
) -> tuple[dict | None, str | None]:
    url = f"{IDENTITY_TOOLKIT}/{endpoint}?key={api_key}"
    try:
        resp = httpx.post(url, json=payload, timeout=30)
    except httpx.HTTPError as exc:
        return None, f"Firebase Auth request failed: {exc}"

    try:
        body = resp.json()
    except json.JSONDecodeError:
        return None, f"Unexpected response HTTP {resp.status_code}: {resp.text}"

    if resp.status_code != 200:
        err = body.get("error", {})
        message = err.get("message", resp.text)
        return None, message
    return body, None


def sign_in_with_password(
    *, api_key: str, email: str, password: str
) -> tuple[dict | None, str | None]:
    return _identity_request(
        api_key=api_key,
        endpoint="accounts:signInWithPassword",
        payload={
            "email": email,
            "password": password,
            "returnSecureToken": True,
        },
    )


def sign_up(*, api_key: str, email: str, password: str) -> tuple[dict | None, str | None]:
    return _identity_request(
        api_key=api_key,
        endpoint="accounts:signUp",
        payload={
            "email": email,
            "password": password,
            "returnSecureToken": True,
        },
    )


def obtain_id_token(
    *,
    api_key: str,
    email: str,
    password: str,
    allow_sign_up: bool,
) -> dict:
    result, err = sign_in_with_password(api_key=api_key, email=email, password=password)
    if result is not None:
        return result

    if allow_sign_up and err == "EMAIL_NOT_FOUND":
        result, sign_up_err = sign_up(api_key=api_key, email=email, password=password)
        if result is not None:
            return result
        print(f"ERROR: Firebase sign-up failed: {sign_up_err}", file=sys.stderr)
        sys.exit(1)

    print(f"ERROR: Firebase sign-in failed: {err}", file=sys.stderr)
    if err == "EMAIL_NOT_FOUND":
        print("       Create the user in Firebase Console or re-run with --sign-up.", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    args = parse_args()

    project_id = (
        args.project
        or _env("FIREBASE_PROJECT_ID")
        or _env("GOOGLE_CLOUD_PROJECT")
        or "medication-companion-dev"
    )
    email = args.email or _env("FIREBASE_TEST_EMAIL")
    password = args.password or _env("FIREBASE_TEST_PASSWORD")

    if not email or not password:
        print(
            "ERROR: Email and password required.\n"
            "       Set FIREBASE_TEST_EMAIL and FIREBASE_TEST_PASSWORD, or use --email / --password.",
            file=sys.stderr,
        )
        sys.exit(1)

    api_key = _resolve_api_key(project_id, args.api_key)
    result = obtain_id_token(
        api_key=api_key,
        email=email,
        password=password,
        allow_sign_up=args.sign_up,
    )

    id_token = result.get("idToken")
    if not id_token:
        print("ERROR: Response missing idToken", file=sys.stderr)
        sys.exit(1)

    if args.print_token_only:
        print(id_token, end="")
        return

    expires_in = result.get("expiresIn", "?")
    local_id = result.get("localId", "?")
    print(f"Project : {project_id}")
    print(f"User    : {email} (uid={local_id})")
    print(f"Expires : {expires_in}s")
    print()
    print(id_token)


if __name__ == "__main__":
    main()
