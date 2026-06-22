"""
backend/auth_broker/assembly.py
Assemble PrescriptionResult from pipeline agent outputs.
"""
from __future__ import annotations

from typing import Any

from agents.agent3_safety import SafetyOutput
from agents.agent4_education import EducationOutput
from agents.agent5_localisation import LocalisationOutput
from schemas import InteractionFinding, PrescriptionResult, ResolvedDrug


def _interactions_from_tool(payload: dict[str, Any]) -> list[InteractionFinding]:
    findings: list[InteractionFinding] = []
    for item in payload.get("interactions") or []:
        if not isinstance(item, dict):
            continue
        findings.append(
            InteractionFinding(
                drug_a=str(item.get("drug_a", "")),
                drug_b=str(item.get("drug_b", "")),
                severity=str(item.get("severity", "NONE")),
                mechanism=str(item.get("mechanism", "")),
                source=str(item.get("source", "current_visit")),
            )
        )
    return findings


def _interactions_from_safety_output(safety: SafetyOutput) -> list[InteractionFinding]:
    return [
        InteractionFinding(
            drug_a=item.drug_a,
            drug_b=item.drug_b,
            severity=item.severity,
            mechanism=item.mechanism,
            source=item.source,
        )
        for item in (safety.interactions or [])
    ]


def assemble_prescription_result(
    session_id: str,
    education: EducationOutput,
    localisation: LocalisationOutput | dict | None,
    *,
    safety_tool: dict[str, Any] | None = None,
    safety_output: SafetyOutput | None = None,
) -> PrescriptionResult:
    loc = localisation or {}
    if isinstance(localisation, LocalisationOutput):
        translated = localisation.translated_text
        audio_url = localisation.audio_url
    else:
        translated = loc.get("translated_text", education.summary)
        audio_url = loc.get("audio_url", "")

    resolved_drugs = [
        ResolvedDrug(
            raw_name=card.display_name,
            generic_name=card.generic_equivalent,
            tag=card.tag,
        )
        for card in (education.drug_cards or [])
    ]

    if safety_tool and (
        safety_tool.get("pairs_checked", 0) > 0 or safety_tool.get("interactions")
    ):
        interactions = _interactions_from_tool(safety_tool)
        overall_severity = str(safety_tool.get("overall_severity") or "NONE")
    elif safety_output and safety_output.interactions:
        interactions = _interactions_from_safety_output(safety_output)
        overall_severity = safety_output.overall_severity or "NONE"
    elif safety_tool:
        interactions = _interactions_from_tool(safety_tool)
        overall_severity = str(safety_tool.get("overall_severity") or "NONE")
    elif safety_output:
        interactions = _interactions_from_safety_output(safety_output)
        overall_severity = safety_output.overall_severity or "NONE"
    else:
        interactions = []
        overall_severity = education.overall_severity or "NONE"

    return PrescriptionResult(
        session_id=session_id,
        resolved_drugs=resolved_drugs,
        interactions=interactions,
        overall_severity=overall_severity,
        explanation_en=education.summary,
        explanation_localised=translated,
        audio_url=audio_url,
        doctor_questions=education.questions_for_doctor or [],
        disclaimer=education.disclaimer,
    )
