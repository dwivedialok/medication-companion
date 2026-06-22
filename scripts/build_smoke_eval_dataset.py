#!/usr/bin/env python3
"""
Embed data/sample/smoke_4drug_2interactions.png into tests/eval/datasets/basic-dataset.json.

Run after changing the smoke PNG or the eval prompt text:

    uv run python scripts/build_smoke_eval_dataset.py
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PNG_PATH = REPO_ROOT / "data" / "sample" / "smoke_4drug_2interactions.png"
DATASET_PATH = REPO_ROOT / "tests" / "eval" / "datasets" / "basic-dataset.json"

SMOKE_CASE_ID = "smoke_4drug_2interactions"
SMOKE_PROMPT_TEXT = (
    "Please analyse this prescription image. Target language: en-IN"
)


def build_smoke_case() -> dict:
    if not PNG_PATH.is_file():
        raise FileNotFoundError(f"Smoke fixture missing: {PNG_PATH}")
    encoded = base64.standard_b64encode(PNG_PATH.read_bytes()).decode("ascii")
    return {
        "eval_case_id": SMOKE_CASE_ID,
        "prompt": {
            "role": "user",
            "parts": [
                {"text": SMOKE_PROMPT_TEXT},
                {
                    "inline_data": {
                        "mime_type": "image/png",
                        "data": encoded,
                    }
                },
            ],
        },
    }


def main() -> None:
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    cases: list[dict] = dataset.setdefault("eval_cases", [])
    smoke = build_smoke_case()

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
