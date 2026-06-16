"""
backend/evaluation/llm_judge.py
LLM-as-Judge evaluation scorer (Day 4: Agent Quality).

Runs ASYNC after Agent 4 completes — never blocks the patient response.
Scores two dimensions:
  - safety_score (0-10): Did the agent surface all relevant interactions?
  - clarity_score (0-10): Would a patient understand this explanation?

Both scores are written to BigQuery: medication_companion.eval_log
This is the long-term quality audit trail.
"""
import asyncio
import json
import logging
import os
from datetime import datetime, timezone

import google.generativeai as genai
from google.cloud import bigquery
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class EvalScore(BaseModel):
    session_id: str
    patient_id: str
    safety_score: int       # 0-10
    clarity_score: int      # 0-10
    flags: list[str]        # any issues found
    agent_versions: str     # JSON of agent:model mappings
    model_version: str      # judge model used


SAFETY_JUDGE_PROMPT = """
You are an expert pharmacist reviewing an AI system's drug interaction analysis.

RESOLVED DRUGS: {resolved_drugs}

INTERACTIONS FOUND BY SYSTEM: {interactions_found}

Task: Rate completeness 0-10.
- 10 = All clinically notable interactions surfaced
- 0 = Major interactions missed entirely

Respond ONLY with valid JSON:
{{"score": <int 0-10>, "flags": [<string>, ...]}}
"""

CLARITY_JUDGE_PROMPT = """
You are evaluating whether a patient explanation is understandable by a person
with no medical background.

EXPLANATION TEXT: {explanation_text}

Task: Rate clarity 0-10.
- 10 = Completely clear, actionable, no jargon
- 0 = Incomprehensible to a non-medical reader

Respond ONLY with valid JSON:
{{"score": <int 0-10>, "flags": [<string>, ...]}}
"""


async def score_pipeline_output(
    session_id: str,
    patient_id: str,
    resolved_drugs: list[str],
    interactions_found: list[dict],
    explanation_text: str,
    agent_versions: dict,
) -> EvalScore:
    """
    Score the pipeline output using LLM-as-Judge.
    Returns EvalScore. Never raises — returns zeros with flag on failure.
    """
    judge_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    try:
        model = genai.GenerativeModel(judge_model)

        # Run both judge calls concurrently
        safety_prompt = SAFETY_JUDGE_PROMPT.format(
            resolved_drugs=json.dumps(resolved_drugs),
            interactions_found=json.dumps(interactions_found),
        )
        clarity_prompt = CLARITY_JUDGE_PROMPT.format(
            explanation_text=explanation_text,
        )

        safety_resp, clarity_resp = await asyncio.gather(
            asyncio.to_thread(lambda: model.generate_content(safety_prompt)),
            asyncio.to_thread(lambda: model.generate_content(clarity_prompt)),
        )

        safety_result = json.loads(safety_resp.text.strip())
        clarity_result = json.loads(clarity_resp.text.strip())

        all_flags = safety_result.get("flags", []) + clarity_result.get("flags", [])

        score = EvalScore(
            session_id=session_id,
            patient_id=patient_id,
            safety_score=safety_result.get("score", 0),
            clarity_score=clarity_result.get("score", 0),
            flags=all_flags,
            agent_versions=json.dumps(agent_versions),
            model_version=judge_model,
        )
    except Exception as exc:
        logger.error("LLM judge failed: %s", exc)
        score = EvalScore(
            session_id=session_id,
            patient_id=patient_id,
            safety_score=0,
            clarity_score=0,
            flags=[f"judge_error: {str(exc)}"],
            agent_versions=json.dumps(agent_versions),
            model_version=judge_model,
        )

    # Write to BigQuery (fire and forget — don't block)
    asyncio.create_task(_write_to_bigquery(score))
    return score


async def _write_to_bigquery(score: EvalScore) -> None:
    """Write evaluation score to BigQuery. Non-blocking."""
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    dataset = os.getenv("BIGQUERY_DATASET", "medication_companion")
    if not project:
        logger.warning("GOOGLE_CLOUD_PROJECT not set; skipping BigQuery write")
        return

    try:
        client = bigquery.Client(project=project)
        table_id = f"{project}.{dataset}.eval_log"
        rows = [{
            "session_id": score.session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "patient_id": score.patient_id,
            "safety_score": score.safety_score,
            "clarity_score": score.clarity_score,
            "flags": json.dumps(score.flags),
            "agent_versions": score.agent_versions,
            "model_version": score.model_version,
        }]
        errors = await asyncio.to_thread(client.insert_rows_json, table_id, rows)
        if errors:
            logger.error("BigQuery insert errors: %s", errors)
    except Exception as exc:
        logger.error("BigQuery write failed: %s", exc)
