"""Tests for ADK event output extraction."""
import json
from types import SimpleNamespace

from agents.agent1_reader import Gate1Reject, ReaderOutput
from agents.agent3_safety import SafetyOutput
from agents.agent4_education import EducationOutput
from pipeline_output import (
    find_education_output,
    find_gate1_reject,
    find_safety_output,
    find_safety_tool_result,
)


def _model_event(author: str, payload: dict) -> SimpleNamespace:
    return SimpleNamespace(
        author=author,
        id="evt-001",
        output=None,
        content=SimpleNamespace(
            parts=[SimpleNamespace(text=json.dumps(payload), thought=False)]
        ),
        actions=SimpleNamespace(state_delta={}),
        get_function_responses=lambda: [],
        get_function_calls=lambda: [],
    )


def _set_model_response_event(author: str, payload: dict) -> SimpleNamespace:
    return SimpleNamespace(
        author=author,
        id="evt-002",
        output=None,
        content=None,
        actions=SimpleNamespace(state_delta={}),
        get_function_calls=lambda: [],
        get_function_responses=lambda: [
            SimpleNamespace(
                name="set_model_response",
                response={"result": payload},
            )
        ],
    )


def test_find_education_output_from_model_content_json():
    events = [
        _model_event(
            "patient_education",
            {
                "drug_cards": [
                    {
                        "display_name": "Telma",
                        "generic_equivalent": "telmisartan",
                        "tag": "NEW",
                    }
                ],
                "interaction_cards": [],
                "summary": "Your prescription includes telmisartan. Please discuss this with your doctor or pharmacist before making any changes.",
                "questions_for_doctor": ["Is telmisartan right for my blood pressure?"],
                "overall_severity": "NONE",
                "disclaimer": "This is for information only. Please discuss this with your doctor or pharmacist before making any changes.",
            },
        )
    ]
    edu = find_education_output(events)
    assert edu is not None
    assert edu.drug_cards[0].generic_equivalent == "telmisartan"


def test_find_education_output_from_set_model_response():
    events = [
        _set_model_response_event(
            "patient_education",
            {
                "drug_cards": [],
                "interaction_cards": [],
                "summary": "No interactions found. Please discuss this with your doctor or pharmacist before making any changes.",
                "questions_for_doctor": ["Should I take these with food?"],
                "overall_severity": "NONE",
                "disclaimer": "This is for information only. Please discuss this with your doctor or pharmacist before making any changes.",
            },
        )
    ]
    assert find_education_output(events) is not None


def test_find_gate1_reject_from_reader_json():
    events = [
        _model_event(
            "prescription_reader",
            {
                "status": "gate1_reject",
                "gate1_reject": {
                    "reason": "Image too blurry",
                    "user_message": "Please retake the photo. Please discuss your medications with your doctor or pharmacist.",
                },
            },
        )
    ]
    reject = find_gate1_reject(events)
    assert reject is not None
    assert reject.reason == "Image too blurry"


def test_find_gate1_reject_from_reader_output_model():
    events = [
        SimpleNamespace(
            author="prescription_reader",
            id="evt-003",
            output=ReaderOutput(
                status="gate1_reject",
                gate1_reject=Gate1Reject(reason="Low confidence"),
            ),
            content=None,
            actions=SimpleNamespace(state_delta={}),
            get_function_responses=lambda: [],
            get_function_calls=lambda: [],
        )
    ]
    reject = find_gate1_reject(events)
    assert reject is not None
    assert reject.reason == "Low confidence"


def test_find_safety_tool_result():
    events = [
        SimpleNamespace(
            author="medication_safety",
            id="evt-safety-tool",
            output=None,
            content=None,
            actions=SimpleNamespace(state_delta={}),
            get_function_calls=lambda: [],
            get_function_responses=lambda: [
                SimpleNamespace(
                    name="check_prescription_interactions",
                    response={
                        "result": {
                            "interactions": [
                                {
                                    "drug_a": "aspirin",
                                    "drug_b": "nimesulide",
                                    "severity": "HIGH",
                                    "mechanism": "Dataset hit.",
                                    "source": "current_visit",
                                }
                            ],
                            "overall_severity": "HIGH",
                            "pairs_checked": 6,
                        }
                    },
                )
            ],
        )
    ]
    payload = find_safety_tool_result(events)
    assert payload is not None
    assert payload["pairs_checked"] == 6
    assert len(payload["interactions"]) == 1


def test_find_safety_output():
    events = [
        _set_model_response_event(
            "medication_safety",
            {
                "interactions": [],
                "overall_severity": "NONE",
                "safe_to_proceed": True,
            },
        )
    ]
    safety = find_safety_output(events)
    assert isinstance(safety, SafetyOutput)
    assert safety.overall_severity == "NONE"
