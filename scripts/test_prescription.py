#!/usr/bin/env python3
"""
scripts/test_prescription.py
Post a prescription image to the local backend and print the result.

Usage:
    python scripts/test_prescription.py <image_path> [options]

Examples:
    python scripts/test_prescription.py ~/Downloads/rx.jpg
    python scripts/test_prescription.py ~/Downloads/rx.jpg --language hi-IN
    python scripts/test_prescription.py ~/Downloads/rx.jpg --url http://localhost:8080
    python scripts/test_prescription.py ~/Downloads/rx.jpg --pretty false
"""
import argparse
import json
import mimetypes
import sys
from pathlib import Path

try:
    import httpx
except ImportError:
    print("ERROR: httpx not installed. Run: pip install httpx")
    sys.exit(1)


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="POST a prescription image to the Medication Companion backend."
    )
    parser.add_argument("image", help="Path to the prescription image file")
    parser.add_argument(
        "--url",
        default="http://localhost:8080",
        help="Base URL of the main service (default: http://localhost:8080)",
    )
    parser.add_argument(
        "--language",
        default="en-IN",
        choices=["en-IN", "hi-IN", "ta-IN", "te-IN", "bn-IN"],
        help="Target language for audio (default: en-IN)",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="Firebase Bearer token (omit when ENVIRONMENT=local — DEV_PATIENT_ID bypass is used)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Request timeout in seconds (default: 120 — pipeline takes ~20-40s)",
    )
    parser.add_argument(
        "--pretty",
        default="true",
        choices=["true", "false"],
        help="Pretty-print JSON output (default: true)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    image_path = Path(args.image).expanduser().resolve()
    if not image_path.exists():
        print(f"ERROR: File not found: {image_path}")
        sys.exit(1)

    if image_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        print(f"WARNING: Unexpected extension '{image_path.suffix}'. Supported: {SUPPORTED_EXTENSIONS}")

    mime_type, _ = mimetypes.guess_type(str(image_path))
    mime_type = mime_type or "image/jpeg"

    headers = {}
    if args.token:
        headers["Authorization"] = f"Bearer {args.token}"

    endpoint = f"{args.url.rstrip('/')}/prescription"

    print(f"→  Image   : {image_path.name}  ({image_path.stat().st_size / 1024:.1f} KB, {mime_type})")
    print(f"→  Endpoint: {endpoint}")
    print(f"→  Language: {args.language}")
    print("   Sending request (this takes ~20-40s for the full pipeline)…\n")

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    try:
        response = httpx.post(
            endpoint,
            files={"image": (image_path.name, image_bytes, mime_type)},
            data={"language": args.language},
            headers=headers,
            timeout=args.timeout,
        )
    except httpx.ConnectError:
        print(f"ERROR: Could not connect to {args.url}")
        print("       Is the backend running?  cd backend && uvicorn main:app --reload --port 8080")
        sys.exit(1)
    except httpx.TimeoutException:
        print(f"ERROR: Request timed out after {args.timeout}s")
        sys.exit(1)

    status_label = "✓" if response.status_code == 200 else "✗"
    print(f"{status_label}  HTTP {response.status_code}")
    print()

    try:
        body = response.json()
    except Exception:
        print("Response (non-JSON):")
        print(response.text)
        sys.exit(0 if response.status_code == 200 else 1)

    if args.pretty == "true":
        print(json.dumps(body, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(body, ensure_ascii=False))

    if response.status_code == 200:
        # Print a short summary for quick visual check
        print()
        print("─" * 50)
        print(f"  Severity   : {body.get('overall_severity', '?')}")
        drugs = body.get("resolved_drugs", [])
        print(f"  Drugs      : {len(drugs)} resolved")
        for d in drugs:
            print(f"               {d.get('raw_name')} → {d.get('generic_name')} [{d.get('tag')}]")
        interactions = body.get("interactions", [])
        print(f"  Interactions: {len(interactions)}")
        for ix in interactions:
            print(f"               {ix.get('drug_a')} + {ix.get('drug_b')} → {ix.get('severity')}")
        print(f"  Audio URL  : {body.get('audio_url', '(none)')}")
        print("─" * 50)

    sys.exit(0 if response.status_code == 200 else 1)


if __name__ == "__main__":
    main()
