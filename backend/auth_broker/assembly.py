"""
backend/auth_broker/assembly.py
Assemble PrescriptionResult from pipeline agent outputs.
"""
from __future__ import annotations

from agents.agent4_education import EducationOutput
from agents.agent5_localisation import LocalisationOutput
from schemas import InteractionFinding, PrescriptionResult, ResolvedDrug


def assemble_prescription_result(
    session_id: str,
    education: EducationOutput,
    localisation: LocalisationOutput | dict | None,
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

    interactions = []
    for card in education.interaction_cards or []:
        parts = card.drug_pair.split("+", 1)
        drug_a = parts[0].strip()
        drug_b = parts[1].strip() if len(parts) > 1 else ""
        interactions.append(
            InteractionFinding(
                drug_a=drug_a,
                drug_b=drug_b,
                severity=card.severity,
                mechanism=card.plain_language,
            )
        )

    return PrescriptionResult(
        session_id=session_id,
        resolved_drugs=resolved_drugs,
        interactions=interactions,
        overall_severity=education.overall_severity or "NONE",
        explanation_en=education.summary,
        explanation_localised=translated,
        audio_url=audio_url,
        doctor_questions=education.questions_for_doctor or [],
        disclaimer=education.disclaimer,
    )
