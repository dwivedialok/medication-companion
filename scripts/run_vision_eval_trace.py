#!/usr/bin/env python3
"""
Run a prescription image through the production Runtime path (GCS + streamQuery),
export a single-case eval trace, and optionally grade with tests/eval/eval_config.yaml.

Use this when `agents-cli eval generate` fails to deliver images to Agent 1 vision
but `agents-cli run --file` / the auth broker path works.

Examples:
    # Smoke fixture → trace only
    uv run python scripts/run_vision_eval_trace.py

    # Custom image, upload to GCS, then grade
    uv run python scripts/run_vision_eval_trace.py \\
      --image ~/rx.jpg --grade

    # Reuse a fixed eval object (no upload)
    uv run python scripts/run_vision_eval_trace.py \\
      --gcs-uri gs://medication-companion-uploads/eval/smoke_4drug_2interactions.png \\
      --grade
"""
from __future__ import annotations

import argparse
import asyncio
import json
import mimetypes
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

DEFAULT_IMAGE = REPO_ROOT / "data" / "sample" / "smoke_4drug_2interactions.png"
DEFAULT_GCS_URI = (
    "gs://medication-companion-uploads/eval/smoke_4drug_2interactions.png"
)
EVAL_CONFIG = REPO_ROOT / "tests" / "eval" / "eval_config.yaml"
TRACES_DIR = REPO_ROOT / "artifacts" / "traces"
GRADE_DIR = REPO_ROOT / "artifacts" / "grade_results"

_PIPELINE_AUTHORS = frozenset(
    {
        "prescription_reader",
        "medication_resolver",
        "medication_safety",
        "patient_education",
        "localisation_audio",
    }
)


def _parse_gcs_uri(gcs_uri: str) -> tuple[str, str]:
    if not gcs_uri.startswith("gs://"):
        raise ValueError(f"Expected gs:// URI, got {gcs_uri!r}")
    path = gcs_uri[len("gs://") :]
    bucket, _, blob = path.partition("/")
    if not bucket or not blob:
        raise ValueError(f"Invalid GCS URI: {gcs_uri}")
    return bucket, blob


def _upload_image(local_path: Path, *, bucket: str, prefix: str) -> str:
    from google.cloud import storage

    mime_type, _ = mimetypes.guess_type(str(local_path))
    mime_type = mime_type or "image/png"
    blob_name = f"{prefix.rstrip('/')}/{uuid.uuid4().hex}_{local_path.name}"
    client = storage.Client()
    blob = client.bucket(bucket).blob(blob_name)
    blob.upload_from_filename(str(local_path), content_type=mime_type)
    return f"gs://{bucket}/{blob_name}", mime_type


def _load_agents_metadata() -> dict:
    """Reuse agent instruction snapshot from a prior agents-cli eval generate trace."""
    traces_root = TRACES_DIR
    if not traces_root.is_dir():
        return {}
    for path in sorted(traces_root.glob("*.json"), reverse=True):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for case in payload.get("eval_cases") or []:
            agents = (case.get("agent_data") or {}).get("agents")
            if agents:
                return agents
    return {}


def _events_to_turn(events: list) -> list[dict]:
    turn_events: list[dict] = []
    for event in events:
        author = getattr(event, "author", None)
        if author not in _PIPELINE_AUTHORS:
            continue
        content = getattr(event, "content", None)
        if content is None:
            continue
        turn_events.append(
            {
                "author": author,
                "content": content.model_dump(mode="json", exclude_none=True),
            }
        )
    return turn_events


def _final_response_text(events: list) -> str:
    from pipeline_output import find_localisation_output

    loc = find_localisation_output(events)
    if loc is not None:
        return json.dumps(loc.model_dump())

    for event in reversed(events):
        content = getattr(event, "content", None)
        if not content or not getattr(content, "parts", None):
            continue
        for part in content.parts:
            text = getattr(part, "text", None)
            if text:
                return text
    return "{}"


def _build_eval_case(
    *,
    eval_case_id: str,
    gcs_uri: str,
    mime_type: str,
    language: str,
    events: list,
) -> dict:
    from auth_broker.agent_client import _content_dict

    prompt = _content_dict(gcs_uri, mime_type, language)
    response_text = _final_response_text(events)
    agents = _load_agents_metadata()
    return {
        "eval_case_id": eval_case_id,
        "prompt": prompt,
        "responses": [
            {
                "response": {
                    "role": "model",
                    "parts": [{"text": response_text}],
                }
            }
        ],
        "agent_data": {
            "agents": agents,
            "turns": [
                {
                    "turn_index": 0,
                    "turn_id": "turn_0",
                    "events": _events_to_turn(events),
                }
            ],
        },
    }


async def _run_pipeline(
    *,
    patient_id: str,
    gcs_uri: str,
    mime_type: str,
    language: str,
) -> tuple[str, list]:
    from auth_broker.agent_client import run_prescription_pipeline

    return await run_prescription_pipeline(
        patient_id=patient_id,
        gcs_uri=gcs_uri,
        mime_type=mime_type,
        language=language,
    )


def _grade_trace(trace_path: Path) -> None:
    GRADE_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "agents-cli",
            "eval",
            "grade",
            "--config",
            str(EVAL_CONFIG),
            "--traces",
            str(trace_path),
            "--output",
            str(GRADE_DIR),
        ],
        check=True,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--image",
        type=Path,
        default=DEFAULT_IMAGE,
        help=f"Local prescription image (default: {DEFAULT_IMAGE.relative_to(REPO_ROOT)})",
    )
    parser.add_argument(
        "--gcs-uri",
        default=None,
        help=(
            "Use an existing gs:// object instead of uploading --image "
            f"(default smoke object: {DEFAULT_GCS_URI})"
        ),
    )
    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help=f"Use --gcs-uri {DEFAULT_GCS_URI} without uploading --image",
    )
    parser.add_argument(
        "--upload-bucket",
        default="medication-companion-uploads",
        help="GCS bucket when uploading --image (default: medication-companion-uploads)",
    )
    parser.add_argument(
        "--upload-prefix",
        default="eval/runs",
        help="Object prefix when uploading --image (default: eval/runs)",
    )
    parser.add_argument(
        "--language",
        default="en-IN",
        choices=["en-IN", "hi-IN", "ta-IN", "te-IN", "bn-IN"],
        help="Target language passed to the pipeline (default: en-IN)",
    )
    parser.add_argument(
        "--patient-id",
        default="eval-vision-smoke",
        help="Firebase-equivalent user id for Runtime (default: eval-vision-smoke)",
    )
    parser.add_argument(
        "--eval-case-id",
        default="smoke_4drug_2interactions",
        help="eval_case_id label written into the trace JSON",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Trace JSON path (default: artifacts/traces/vision_eval_<timestamp>.json)",
    )
    parser.add_argument(
        "--grade",
        action="store_true",
        help="Run agents-cli eval grade on the exported trace",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.gcs_uri:
        gcs_uri = args.gcs_uri
        bucket, _ = _parse_gcs_uri(gcs_uri)
        mime_type, _ = mimetypes.guess_type(gcs_uri)
        mime_type = mime_type or "image/png"
        print(f"Using existing GCS object: {gcs_uri}")
    elif args.skip_upload:
        gcs_uri = DEFAULT_GCS_URI
        mime_type = "image/png"
        print(f"Using default eval object: {gcs_uri}")
    else:
        image_path = args.image.expanduser().resolve()
        if not image_path.is_file():
            print(f"ERROR: image not found: {image_path}", file=sys.stderr)
            sys.exit(1)
        gcs_uri, mime_type = _upload_image(
            image_path,
            bucket=args.upload_bucket,
            prefix=args.upload_prefix,
        )
        print(f"Uploaded {image_path.name} → {gcs_uri}")

    print("Running pipeline via Agent Runtime (production gs:// path)…")
    session_id, events = asyncio.run(
        _run_pipeline(
            patient_id=args.patient_id,
            gcs_uri=gcs_uri,
            mime_type=mime_type,
            language=args.language,
        )
    )
    print(f"Session {session_id} — {len(events)} events")

    from pipeline_output import find_gate1_reject, find_safety_tool_result

    gate1 = find_gate1_reject(events)
    safety = find_safety_tool_result(events) or {}
    if gate1:
        print(f"Gate 1 reject: {gate1.reason}")
    else:
        pairs = safety.get("pairs_checked", 0)
        severity = safety.get("overall_severity", "NONE")
        interactions = len(safety.get("interactions") or [])
        print(
            f"Gate 1 ok — pairs_checked={pairs}, "
            f"interactions={interactions}, severity={severity}"
        )

    eval_case = _build_eval_case(
        eval_case_id=args.eval_case_id,
        gcs_uri=gcs_uri,
        mime_type=mime_type,
        language=args.language,
        events=events,
    )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    trace_path = args.output or (TRACES_DIR / f"vision_eval_{timestamp}.json")
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    trace_path.write_text(
        json.dumps({"eval_cases": [eval_case]}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote trace: {trace_path.relative_to(REPO_ROOT)}")

    if args.grade:
        print("Grading with tests/eval/eval_config.yaml …")
        _grade_trace(trace_path)
        print(f"Results in {GRADE_DIR.relative_to(REPO_ROOT)}/results_*.html")


if __name__ == "__main__":
    main()
