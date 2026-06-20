"""
backend/pipeline_output.py
Extract structured agent outputs from ADK runner events.

SequentialAgent (legacy path) puts output_schema results in model content JSON,
not always on ``event.output``. Agents with tools use ``set_model_response``.
"""
import json
import logging
import re
from typing import Any, Callable, TypeVar

from pydantic import BaseModel, ValidationError

from agents.agent1_reader import Gate1Reject, ReaderOutput
from agents.agent4_education import EducationOutput
from agents.agent5_localisation import LocalisationOutput

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_JSON_FENCE_RE = re.compile(
    r"^```(?:json)?\s*\n?(.*?)\n?```\s*$",
    re.DOTALL | re.IGNORECASE,
)


def _strip_json_fence(text: str) -> str:
    text = text.strip()
    match = _JSON_FENCE_RE.match(text)
    return match.group(1).strip() if match else text


def _event_text(event: Any) -> str:
    content = getattr(event, "content", None)
    if not content or not getattr(content, "parts", None):
        return ""
    return "".join(
        part.text
        for part in content.parts
        if getattr(part, "text", None) and not getattr(part, "thought", False)
    )


def _set_model_response_payload(event: Any) -> dict | None:
    get_responses = getattr(event, "get_function_responses", None)
    if not get_responses:
        return None
    for resp in get_responses() or []:
        if resp.name != "set_model_response":
            continue
        raw = resp.response
        if isinstance(raw, dict):
            if "result" in raw:
                raw = raw["result"]
            if isinstance(raw, dict):
                return raw
    return None


def _coerce_model(model_cls: type[T], data: Any) -> T | None:
    if isinstance(data, model_cls):
        return data
    if isinstance(data, dict):
        try:
            return model_cls.model_validate(data)
        except ValidationError:
            return None
    if isinstance(data, str) and data.strip():
        try:
            return model_cls.model_validate(json.loads(_strip_json_fence(data)))
        except (json.JSONDecodeError, ValidationError):
            return None
    return None


def _iter_candidate_dicts(event: Any) -> list[dict]:
    candidates: list[dict] = []

    output = getattr(event, "output", None)
    if isinstance(output, dict):
        candidates.append(output)
    elif isinstance(output, BaseModel):
        candidates.append(output.model_dump())

    fc_payload = _set_model_response_payload(event)
    if fc_payload:
        candidates.append(fc_payload)

    text = _event_text(event)
    if text:
        try:
            parsed = json.loads(_strip_json_fence(text))
            if isinstance(parsed, dict):
                candidates.append(parsed)
        except json.JSONDecodeError:
            pass

    actions = getattr(event, "actions", None)
    state_delta = getattr(actions, "state_delta", None) if actions else None
    if isinstance(state_delta, dict):
        for value in state_delta.values():
            if isinstance(value, dict):
                candidates.append(value)
            elif isinstance(value, str) and value.strip():
                try:
                    parsed = json.loads(_strip_json_fence(value))
                    if isinstance(parsed, dict):
                        candidates.append(parsed)
                except json.JSONDecodeError:
                    pass

    return candidates


def extract_agent_output(
    events: list,
    *,
    agent_name: str,
    model_cls: type[T],
    match: Callable[[dict], bool] | None = None,
) -> T | None:
    """Return the last structured output for ``agent_name`` from runner events."""
    predicate = match or (lambda _data: True)

    for event in reversed(events):
        if getattr(event, "author", "") != agent_name:
            continue
        for data in _iter_candidate_dicts(event):
            if not predicate(data):
                continue
            parsed = _coerce_model(model_cls, data)
            if parsed is not None:
                return parsed

    for event in reversed(events):
        for data in _iter_candidate_dicts(event):
            if not predicate(data):
                continue
            parsed = _coerce_model(model_cls, data)
            if parsed is not None:
                return parsed

    return None


def find_gate1_reject(events: list) -> Gate1Reject | None:
    for event in reversed(events):
        for data in _iter_candidate_dicts(event):
            if data.get("status") == "gate1_reject":
                reject_data = data.get("gate1_reject") or {}
                if isinstance(reject_data, dict):
                    return Gate1Reject(**reject_data)
            reader = _coerce_model(ReaderOutput, data)
            if reader is not None and reader.gate1_reject is not None:
                return reader.gate1_reject
    return None


def find_education_output(events: list) -> EducationOutput | None:
    return extract_agent_output(
        events,
        agent_name="patient_education",
        model_cls=EducationOutput,
        match=lambda data: "drug_cards" in data,
    )


def find_localisation_output(events: list) -> LocalisationOutput | None:
    return extract_agent_output(
        events,
        agent_name="localisation_audio",
        model_cls=LocalisationOutput,
        match=lambda data: "translated_text" in data,
    )


def log_event_authors(events: list, session_id: str) -> None:
    """Debug helper when pipeline output extraction fails."""
    summary = [
        f"{getattr(e, 'author', '?')}:{getattr(e, 'id', '')[:8]}"
        for e in events
    ]
    logger.error(
        "Pipeline event authors (session=%s, count=%d): %s",
        session_id,
        len(events),
        ", ".join(summary) if summary else "(none)",
    )
