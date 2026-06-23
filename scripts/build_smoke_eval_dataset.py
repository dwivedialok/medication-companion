#!/usr/bin/env python3
"""
Embed the smoke prescription fixture into tests/eval/datasets/basic-dataset.json.

Agent Runtime (used by `agents-cli eval generate`) reads prescription images via
gs:// file_data — the same path as production auth-broker traffic. inline_data
base64 in the eval JSON is stored in the dataset but often does not reach Agent 1
vision on Runtime, which makes the smoke case look like a false Gate 1 reject.

Run after changing the smoke PNG or eval prompt text:

    # Recommended — vision works on deployed Runtime (upload once):
    gsutil cp data/sample/smoke_4drug_2interactions.png \\
      gs://medication-companion-uploads/eval/smoke_4drug_2interactions.png

    uv run python scripts/build_smoke_eval_dataset.py \\
      --gcs-uri gs://medication-companion-uploads/eval/smoke_4drug_2interactions.png

    # Fallback — inline base64 (fine for dataset validation only, not Runtime eval):
    uv run python scripts/build_smoke_eval_dataset.py --inline
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PNG_PATH = REPO_ROOT / "data" / "sample" / "smoke_4drug_2interactions.png"
DATASET_PATH = REPO_ROOT / "tests" / "eval" / "datasets" / "basic-dataset.json"

SMOKE_CASE_ID = "smoke_4drug_2interactions"
SMOKE_PROMPT_TEXT = (
    "Please analyse this prescription image. Target language: en-IN"
)
DEFAULT_GCS_URI = (
    "gs://medication-companion-uploads/eval/smoke_4drug_2interactions.png"
)


def _image_part(*, gcs_uri: str | None, inline: bool) -> dict:
    if gcs_uri:
        if not gcs_uri.startswith("gs://"):
            raise ValueError(f"GCS URI must start with gs:// — got {gcs_uri!r}")
        return {
            "file_data": {
                "mime_type": "image/png",
                "file_uri": gcs_uri,
            }
        }
    if inline:
        if not PNG_PATH.is_file():
            raise FileNotFoundError(f"Smoke fixture missing: {PNG_PATH}")
        encoded = base64.standard_b64encode(PNG_PATH.read_bytes()).decode("ascii")
        return {
            "inline_data": {
                "mime_type": "image/png",
                "data": encoded,
            }
        }
    raise ValueError("Provide --gcs-uri or --inline")


def build_smoke_case(*, gcs_uri: str | None, inline: bool) -> dict:
    return {
        "eval_case_id": SMOKE_CASE_ID,
        "prompt": {
            "role": "user",
            "parts": [
                {"text": SMOKE_PROMPT_TEXT},
                _image_part(gcs_uri=gcs_uri, inline=inline),
            ],
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--gcs-uri",
        default=None,
        help=(
            "Use file_data with this gs:// URI. Defaults to EVAL_SMOKE_GCS_URI env var "
            f"or {DEFAULT_GCS_URI} when --inline is not set."
        ),
    )
    group.add_argument(
        "--inline",
        action="store_true",
        help="Embed PNG as inline_data base64 instead of gs:// file_data.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.inline:
        smoke = build_smoke_case(gcs_uri=None, inline=True)
        print(
            "WARNING: inline_data often fails to reach Agent 1 on deployed Runtime. "
            "Use --gcs-uri for meaningful eval scores.",
            file=sys.stderr,
        )
    else:
        gcs_uri = args.gcs_uri or os.getenv("EVAL_SMOKE_GCS_URI", DEFAULT_GCS_URI)
        smoke = build_smoke_case(gcs_uri=gcs_uri, inline=False)
        print(f"Using file_data: {gcs_uri}")

    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    cases: list[dict] = dataset.setdefault("eval_cases", [])

    replaced = False
    for index, case in enumerate(cases):
        if case.get("eval_case_id") == SMOKE_CASE_ID:
            cases[index] = smoke
            replaced = True
            break
    if not replaced:
        cases.append(smoke)

    DATASET_PATH.write_text(
        json.dumps(dataset, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    action = "Updated" if replaced else "Appended"
    print(f"{action} {SMOKE_CASE_ID} in {DATASET_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
