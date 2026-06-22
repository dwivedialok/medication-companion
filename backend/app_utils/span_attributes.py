"""
backend/app_utils/span_attributes.py
Structured OpenTelemetry span attributes for policy callbacks (Day 4 §4.2).

Attributes ride the Agent Runtime Cloud Trace exporter — no custom OTel SDK setup.
"""
from __future__ import annotations

import hashlib
from typing import Any

from opentelemetry import trace


def hash_patient_id(patient_id: str | None) -> str:
    """SHA-256 of patient_id; empty string when missing."""
    if not patient_id:
        return ""
    return hashlib.sha256(patient_id.encode("utf-8")).hexdigest()


def set_span_attributes(**attributes: Any) -> None:
    """Set attributes on the current span when recording."""
    span = trace.get_current_span()
    if span is None or not span.is_recording():
        return
    for key, value in attributes.items():
        if value is None:
            continue
        span.set_attribute(key, value)


def annotate_policy_callback(
    *,
    agent_name: str,
    patient_id: str | None,
    policy_decision: str,
    image_classification: str | None = None,
    violation_class: str | None = None,
    model: str | None = None,
) -> None:
    """Common attribute bundle for policy gate callbacks."""
    attrs: dict[str, Any] = {
        "agent_name": agent_name,
        "patient_id_hash": hash_patient_id(patient_id),
        "policy_decision": policy_decision,
    }
    if image_classification is not None:
        attrs["image_classification"] = image_classification
    if violation_class is not None:
        attrs["violation_class"] = violation_class
    if model is not None:
        attrs["model"] = model
    set_span_attributes(**attrs)
