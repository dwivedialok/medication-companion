#!/usr/bin/env python3
"""
scripts/inspect_memory_bank.py
List cross-visit medication history stored in Vertex AI Memory Bank for a patient.

Uses the same ADK VertexAiMemoryBankService + app_name/user_id keys as the pipeline.

Usage:
    uv run python scripts/inspect_memory_bank.py --patient-id FIREBASE_UID
    uv run python scripts/inspect_memory_bank.py --patient-id vA00oOHFvxW1zMKCLSy5Mwm3Wgg1

Requires ADC: gcloud auth application-default login
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _default_engine_id() -> str | None:
    metadata = _REPO_ROOT / "deployment_metadata.json"
    if not metadata.exists():
        return None
    try:
        data = json.loads(metadata.read_text(encoding="utf-8"))
        resource = str(data.get("remote_agent_runtime_id", "")).strip()
        if resource:
            return resource.rsplit("/", 1)[-1]
    except (json.JSONDecodeError, OSError, IndexError):
        return None
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect Vertex AI Memory Bank visits for a patient."
    )
    parser.add_argument(
        "--patient-id",
        required=True,
        help="Firebase UID (same as pipeline user_id / Memory Bank scope)",
    )
    parser.add_argument(
        "--project",
        default=None,
        help="GCP project (default: GOOGLE_CLOUD_PROJECT or medication-companion-dev)",
    )
    parser.add_argument(
        "--location",
        default="us-central1",
        help="Vertex region (default: us-central1)",
    )
    parser.add_argument(
        "--engine-id",
        default=_default_engine_id(),
        help="Reasoning Engine id (default: from deployment_metadata.json)",
    )
    parser.add_argument(
        "--app-name",
        default="backend",
        help="ADK App.name / Memory Bank app_name (default: backend)",
    )
    parser.add_argument(
        "--query",
        default="medication history",
        help="Semantic search query passed to search_memory",
    )
    return parser.parse_args()


def _parse_visit_text(text: str) -> dict | None:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    required = {"visit_timestamp", "resolved_drugs", "severity_summary"}
    if not required <= data.keys():
        return None
    return data


async def inspect_memory(args: argparse.Namespace) -> int:
    import os

    project = args.project or os.getenv("GOOGLE_CLOUD_PROJECT", "medication-companion-dev")
    if not args.engine_id:
        print(
            "ERROR: --engine-id required (deployment_metadata.json missing or empty).",
            file=sys.stderr,
        )
        return 1

    from google.adk.memory import VertexAiMemoryBankService

    print("Memory Bank inspect")
    print(f"  project     : {project}")
    print(f"  location    : {args.location}")
    print(f"  engine_id   : {args.engine_id}")
    print(f"  app_name    : {args.app_name}")
    print(f"  patient_id  : {args.patient_id}")
    print(f"  search_query: {args.query!r}")
    print()

    svc = VertexAiMemoryBankService(
        project=project,
        location=args.location,
        agent_engine_id=args.engine_id,
    )

    try:
        response = await svc.search_memory(
            app_name=args.app_name,
            user_id=args.patient_id,
            query=args.query,
        )
    except Exception as exc:
        print(f"ERROR: search_memory failed: {exc}", file=sys.stderr)
        return 1

    memories = response.memories or []
    print(f"Raw memories returned: {len(memories)}")
    if not memories:
        print()
        print("No memories found. Common causes:")
        print("  - First visit for this patient (nothing written yet)")
        print("  - MEMORY_BACKEND=local on Agent Runtime (no Vertex persistence)")
        print("  - Memory write skipped (check logs for 'Saved visit to memory')")
        print("  - Wrong patient_id or app_name")
        return 0

    parsed_visits: list[dict] = []
    for index, entry in enumerate(memories):
        text = ""
        if entry.content and entry.content.parts:
            text = next((part.text for part in entry.content.parts if part.text), "")
        visit = _parse_visit_text(text) if text else None
        print(f"\n--- memory[{index}] ---")
        if visit is not None:
            parsed_visits.append(visit)
            print(json.dumps(visit, indent=2, ensure_ascii=False))
        elif text:
            print("(unparsed memory text)")
            print(text[:500] + ("..." if len(text) > 500 else ""))
        else:
            print("(empty content)")

    print()
    print(f"Parsed visit records: {len(parsed_visits)} / {len(memories)}")
    if parsed_visits:
        all_generics: set[str] = set()
        for visit in parsed_visits:
            for drug in visit.get("resolved_drugs") or []:
                all_generics.add(str(drug).lower())
        print(f"Distinct generics across visits: {sorted(all_generics)}")
    return 0


def main() -> None:
    args = parse_args()
    raise SystemExit(asyncio.run(inspect_memory(args)))


if __name__ == "__main__":
    main()
