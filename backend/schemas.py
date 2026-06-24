"""
backend/schemas.py
Shared Pydantic models for the /prescription API response.
These are the external-facing contracts — distinct from internal agent output schemas.
"""
from typing import Literal

from pydantic import BaseModel


class ResolvedDrug(BaseModel):
    raw_name: str
    generic_name: str
    drug_class: str | None = None
    tag: str  # NEW | EXISTING | UNRESOLVED


class InteractionFinding(BaseModel):
    drug_a: str
    drug_b: str
    severity: str  # HIGH | MODERATE | LOW | INFO | NONE
    mechanism: str
    source: str = "current_visit"  # current_visit | cross_visit


class EvalScores(BaseModel):
    safety_score: int | None = None
    clarity_score: int | None = None


class PrescriptionResult(BaseModel):
    session_id: str
    resolved_drugs: list[ResolvedDrug]
    interactions: list[InteractionFinding]
    overall_severity: Literal["HIGH", "MODERATE", "LOW", "INFO", "NONE"]
    explanation_en: str
    explanation_localised: str
    audio_url: str
    doctor_questions: list[str]
    disclaimer: str
    eval_scores: EvalScores | None = None


class JobError(BaseModel):
    code: Literal["gate1_reject", "pipeline_error", "internal_error"]
    message: str
    reason: str | None = None


class PrescriptionJobStatus(BaseModel):
    job_id: str
    patient_id: str
    status: Literal["pending", "processing", "done", "failed"]
    created_at: str
    updated_at: str
    result: PrescriptionResult | None = None
    error: JobError | None = None


class PrescriptionJobEnqueueResponse(BaseModel):
    job_id: str
    status: Literal["pending"] = "pending"
