#!/usr/bin/env python3
"""
scripts/test_prescription.py
Post a prescription image via the auth broker (GCS upload + analysis).

Usage:
    python scripts/test_prescription.py <image_path> [options]

Examples:
    python scripts/test_prescription.py ~/Downloads/rx.jpg
    python scripts/test_prescription.py ~/Downloads/rx.jpg --language hi-IN
    python scripts/test_prescription.py ~/Downloads/rx.jpg --url http://localhost:8080
"""
import argparse
import json
import mimetypes
import sys
from pathlib import Path

try:
    import httpx
except ImportError:
    print("ERROR: httpx not installed. Run: uv sync")
    sys.exit(1)


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="POST a prescription image via the auth broker."
    )
    parser.add_argument("image", help="Path to the prescription image file")
    parser.add_argument(
        "--url",
        default="http://localhost:8080",
        help="Auth broker base URL (default: http://localhost:8080)",
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
        "--upload-mode",
        default="auto",
        choices=["auto", "signed", "direct"],
        help="auto: try signed URL, fall back to /upload-direct on failure (default: auto)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Analysis timeout in seconds (default: 120)",
    )
    parser.add_argument(
        "--pretty",
        default="true",
        choices=["true", "false"],
        help="Pretty-print JSON output (default: true)",
    )
    return parser.parse_args()


def _poll_job(base: str, headers: dict, job_id: str, max_wait: int) -> dict:
    """Poll GET /jobs/{id} until done or failed."""
    import time

    delays = [2, 3, 5, 5, 10, 10, 15, 15, 15, 10]
    elapsed = 0
    for delay in delays:
        if elapsed >= max_wait:
            break
        time.sleep(delay)
        elapsed += delay
        resp = httpx.get(
            f"{base}/jobs/{job_id}",
            headers=headers,
            timeout=30,
        )
        if resp.status_code != 200:
            print(f"ERROR: GET /jobs/{job_id} HTTP {resp.status_code}")
            print(resp.text[:500])
            sys.exit(1)
        if not resp.content.strip():
            print(f"ERROR: GET /jobs/{job_id} returned empty body (HTTP 200).")
            print(
                "       If using the Hosting URL, redeploy firebase.json so /jobs/** "
                "rewrites to the broker:\n"
                "         firebase deploy --only hosting --project $GCP_PROJECT"
            )
            sys.exit(1)
        try:
            job = resp.json()
        except json.JSONDecodeError:
            preview = resp.text[:300].replace("\n", " ")
            print(f"ERROR: GET /jobs/{job_id} returned non-JSON (HTTP 200).")
            print(f"       Body preview: {preview!r}")
            print(
                "       Redeploy Hosting with /jobs/** rewrite, or poll the broker "
                "Cloud Run URL directly with the same Bearer token."
            )
            sys.exit(1)
        status = job.get("status")
        print(f"   Job status: {status}")
        if status == "done":
            result = job.get("result")
            if not result:
                print("ERROR: Job done but result missing")
                sys.exit(1)
            return result
        if status == "failed":
            err = job.get("error") or {}
            code = err.get("code", "pipeline_error")
            message = err.get("message", "Analysis failed.")
            if code == "gate1_reject":
                print(f"✗  HTTP 422 (gate1_reject)\n\n{json.dumps(job, indent=2)}")
                sys.exit(0)
            print(f"✗  Job failed: {message}\n")
            sys.exit(1)
    print(f"ERROR: Job did not complete within {max_wait}s")
    sys.exit(1)


def _print_result(body: dict, pretty: str) -> None:
    if pretty == "true":
        print(json.dumps(body, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(body, ensure_ascii=False))
    print()
    print("─" * 50)
    print(f"  Severity   : {body.get('overall_severity', '?')}")
    drugs = body.get("resolved_drugs", [])
    print(f"  Drugs      : {len(drugs)} resolved")
    for d in drugs:
        print(
            f"               {d.get('raw_name')} → {d.get('generic_name')} "
            f"[{d.get('tag')}]"
        )
    interactions = body.get("interactions", [])
    print(f"  Interactions: {len(interactions)}")
    for ix in interactions:
        print(
            f"               {ix.get('drug_a')} + {ix.get('drug_b')} "
            f"→ {ix.get('severity')}"
        )
    print(f"  Audio URL  : {body.get('audio_url', '(none)')}")
    print("─" * 50)


def main() -> None:
    args = parse_args()

    image_path = Path(args.image).expanduser().resolve()
    if not image_path.exists():
        print(f"ERROR: File not found: {image_path}")
        sys.exit(1)

    if image_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        print(
            f"WARNING: Unexpected extension '{image_path.suffix}'. "
            f"Supported: {SUPPORTED_EXTENSIONS}"
        )

    mime_type, _ = mimetypes.guess_type(str(image_path))
    mime_type = mime_type or "image/jpeg"

    headers = {"Content-Type": "application/json"}
    if args.token:
        headers["Authorization"] = f"Bearer {args.token}"

    base = args.url.rstrip("/")

    print(f"→  Image   : {image_path.name}  ({image_path.stat().st_size / 1024:.1f} KB, {mime_type})")
    print(f"→  Broker  : {base}")
    print(f"→  Language: {args.language}")

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    # Step 1–2: upload image to GCS
    gcs_uri = None
    content_type = mime_type
    use_direct = args.upload_mode == "direct"

    if args.upload_mode != "direct":
        print("   [1/3] Requesting GCS upload URL…")
        try:
            upload_resp = httpx.post(
                f"{base}/upload-url",
                headers=headers,
                json={"content_type": mime_type},
                timeout=30,
            )
        except httpx.ConnectError:
            print(f"ERROR: Could not connect to {base}")
            print("       Start auth broker: make auth-broker")
            sys.exit(1)

        if upload_resp.status_code == 200:
            upload_data = upload_resp.json()
            gcs_uri = upload_data["gcs_uri"]
            signed_url = upload_data["upload_url"]
            content_type = upload_data.get("content_type", mime_type)
            print(f"   [2/3] Uploading to {gcs_uri}…")
            put_resp = httpx.put(
                signed_url,
                headers={"Content-Type": content_type},
                content=image_bytes,
                timeout=60,
            )
            if put_resp.status_code < 200 or put_resp.status_code >= 300:
                print(f"ERROR: GCS upload failed HTTP {put_resp.status_code}")
                sys.exit(1)
        elif args.upload_mode == "signed":
            print(f"ERROR: upload-url failed HTTP {upload_resp.status_code}")
            print(upload_resp.text)
            sys.exit(1)
        else:
            use_direct = True
            print("   Signed URL unavailable — falling back to /upload-direct (local dev)")

    if use_direct:
        print("   [1/2] Uploading via broker /upload-direct…")
        try:
            direct_resp = httpx.post(
                f"{base}/upload-direct",
                headers={k: v for k, v in headers.items() if k != "Content-Type"},
                files={"image": (image_path.name, image_bytes, mime_type)},
                timeout=60,
            )
        except httpx.ConnectError:
            print(f"ERROR: Could not connect to {base}")
            sys.exit(1)
        if direct_resp.status_code != 200:
            print(f"ERROR: upload-direct failed HTTP {direct_resp.status_code}")
            try:
                err = direct_resp.json()
                print(err.get("message") or direct_resp.text)
            except Exception:
                print(direct_resp.text)
            print(
                "\nTip: local dev still needs a real GCS bucket. "
                "Run: ./scripts/setup_gcp.sh --project medication-companion-dev"
            )
            sys.exit(1)
        direct_data = direct_resp.json()
        gcs_uri = direct_data["gcs_uri"]
        content_type = direct_data.get("content_type", mime_type)
        print(f"   Uploaded to {gcs_uri}")

    # Step 3: analyse (sync 200 or async 202 + poll)
    print("   Running pipeline (~20-40s)…\n")
    try:
        response = httpx.post(
            f"{base}/prescription",
            headers=headers,
            json={
                "gcs_uri": gcs_uri,
                "language": args.language,
                "content_type": content_type,
            },
            timeout=args.timeout,
        )
    except httpx.TimeoutException:
        print(f"ERROR: Request timed out after {args.timeout}s")
        sys.exit(1)

    if response.status_code == 202:
        try:
            enqueue = response.json()
        except Exception:
            print(response.text)
            sys.exit(1)
        job_id = enqueue.get("job_id")
        if not job_id:
            print("ERROR: Async response missing job_id")
            sys.exit(1)
        print(f"   Job enqueued: {job_id}")
        body = _poll_job(base, headers, job_id, args.timeout)
        print("✓  HTTP 200 (async job complete)\n")
        _print_result(body, args.pretty)
        sys.exit(0)

    status_label = "✓" if response.status_code == 200 else "✗"
    print(f"{status_label}  HTTP {response.status_code}\n")

    try:
        body = response.json()
    except Exception:
        print(response.text)
        sys.exit(0 if response.status_code == 200 else 1)

    if response.status_code == 200:
        _print_result(body, args.pretty)
        sys.exit(0)

    if args.pretty == "true":
        print(json.dumps(body, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(body, ensure_ascii=False))

    sys.exit(1)


if __name__ == "__main__":
    main()
