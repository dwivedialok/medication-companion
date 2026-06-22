"""Tests for PrescriptionResult assembly."""
from __future__ import annotations

from auth_broker.assembly import assemble_prescription_result
from agents.agent3_safety import Interaction, SafetyOutput
from agents.agent4_education import DrugCard, EducationOutput


def _education(**overrides) -> EducationOutput:
    base = {
        "drug_cards": [
            DrugCard(display_name="Ecosprin", generic_equivalent="aspirin", tag="NEW"),
        ],
        "interaction_cards": [
            {
                "drug_pair": "Ecosprin and Warf",
                "severity": "HIGH",
                "plain_language": "Hallucinated pair.",
            }
        ],
        "summary": "Summary. Please discuss this with your doctor or pharmacist before making any changes.",
        "questions_for_doctor": ["Question?"],
        "overall_severity": "HIGH",
    }
    base.update(overrides)
    return EducationOutput.model_validate(base)


def test_assembly_prefers_safety_tool_over_education_cards():
    safety_tool = {
        "interactions": [
            {
                "drug_a": "aspirin",
                "drug_b": "nimesulide",
                "severity": "HIGH",
                "mechanism": "Dataset hit.",
                "source": "current_visit",
            },
            {
                "drug_a": "metronidazole",
                "drug_b": "warfarin",
                "severity": "HIGH",
                "mechanism": "Dataset hit.",
                "source": "current_visit",
            },
        ],
        "overall_severity": "HIGH",
        "pairs_checked": 6,
    }
    result = assemble_prescription_result(
        "sess-1",
        _education(),
        None,
        safety_tool=safety_tool,
    )
    assert len(result.interactions) == 2
    assert result.interactions[0].drug_a == "aspirin"
    assert result.interactions[0].drug_b == "nimesulide"
    assert result.interactions[1].drug_a == "metronidazole"
    assert "Ecosprin and Warf" not in {i.drug_a for i in result.interactions}


def test_assembly_falls_back_to_safety_output():
    safety = SafetyOutput(
        interactions=[
            Interaction(
                drug_a="aspirin",
                drug_b="nimesulide",
                severity="HIGH",
                mechanism="Dataset hit.",
                source="current_visit",
            )
        ],
        overall_severity="HIGH",
        safe_to_proceed=False,
    )
    result = assemble_prescription_result(
        "sess-2",
        _education(overall_severity="MODERATE"),
        None,
        safety_output=safety,
    )
    assert len(result.interactions) == 1
    assert result.overall_severity == "HIGH"
