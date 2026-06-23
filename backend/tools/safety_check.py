"""
backend/tools/safety_check.py
Deterministic drug-drug interaction checking for Agent 3.

Builds the full pair list in Python (current visit + cross-visit memory),
calls interaction_lookup once per unique pair, and returns a SafetyOutput-shaped
dict. Only dataset-backed interactions are emitted — no LLM pharmacology fallback.
"""
from __future__ import annotations

import logging
from typing import Any

from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext

from memory.memory_service import MemoryServiceWrapper
from tools.drug_normalize import canonical_pair, normalize_generic
from tools.interaction_lookup import interaction_lookup
from tools.pipeline_state import generics_from_resolved_state

logger = logging.getLogger(__name__)

_SEVERITY_RANK = {"HIGH": 4, "MODERATE": 3, "LOW": 2, "INFO": 1, "NONE": 0}


def _unique_generics(names: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for name in names:
        generic = normalize_generic(name)
        if generic and generic not in seen:
            seen.add(generic)
            out.append(generic)
    return out


def _history_generics(visits: list[dict[str, Any]] | None) -> list[str]:
    names: list[str] = []
    for visit in visits or []:
        names.extend(visit.get("resolved_drugs") or [])
    return _unique_generics(names)


def _highest_severity(severities: list[str]) -> str:
    if not severities:
        return "NONE"
    return max(severities, key=lambda s: _SEVERITY_RANK.get(s, 0))


def _mechanism_text(lookup: dict[str, Any]) -> str:
    mechanism = (lookup.get("mechanism") or "").strip()
    if mechanism:
        return mechanism
    severity = lookup.get("severity", "INFO")
    a = lookup.get("generic_a", "drug_a")
    b = lookup.get("generic_b", "drug_b")
    return (
        f"Dataset records a {severity.lower()} interaction between {a} and {b}. "
        "Please discuss this with your doctor or pharmacist."
    )


def compute_prescription_safety(
    current_generics: list[str],
    history_visits: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Check all unique drug pairs deterministically.

    Returns a dict matching agents.agent3_safety.SafetyOutput.
    """
    current = _unique_generics(current_generics)
    history = _history_generics(history_visits)

    checked: set[tuple[str, str]] = set()
    interactions: list[dict[str, Any]] = []

    def _check_pair(a: str, b: str, source: str) -> None:
        pair = canonical_pair(a, b)
        if not pair[0] or not pair[1] or pair[0] == pair[1]:
            return
        if pair in checked:
            return
        checked.add(pair)

        lookup = interaction_lookup(pair[0], pair[1])
        if lookup.get("source") != "dataset":
            return
        severity = lookup.get("severity", "NONE")
        if severity == "NONE":
            return

        interactions.append(
            {
                "drug_a": lookup["generic_a"],
                "drug_b": lookup["generic_b"],
                "severity": severity,
                "mechanism": _mechanism_text(lookup),
                "source": source,
            }
        )

    for i, drug_a in enumerate(current):
        for drug_b in current[i + 1 :]:
            _check_pair(drug_a, drug_b, "current_visit")

    history_only = [g for g in history if g not in set(current)]
    for drug_a in current:
        for drug_b in history_only:
            _check_pair(drug_a, drug_b, "cross_visit")

    severities = [item["severity"] for item in interactions]
    overall = _highest_severity(severities)
    return {
        "interactions": interactions,
        "overall_severity": overall,
        "safe_to_proceed": overall != "HIGH",
        "pairs_checked": len(checked),
        "current_generics": current,
        "history_generics": history_only,
        "prior_visit_generics": history,
    }


def create_safety_check_tool(
    memory_service: MemoryServiceWrapper,
) -> FunctionTool:
    """Return a FunctionTool that runs the deterministic safety check."""

    async def check_prescription_interactions(
        tool_context: ToolContext,
    ) -> dict[str, Any]:
        """
        Check all drug pairs for the current prescription against drugs.db and
        the patient's cross-visit medication history.

        Reads resolved generics from session state (filtered by Agent 1 allowlist).
        Returns SafetyOutput fields plus pairs_checked for observability.
        """
        current = generics_from_resolved_state(tool_context.state)
        if not current:
            logger.info(
                "No resolved generics in session state for patient %s",
                tool_context.user_id,
            )
            return {
                "interactions": [],
                "overall_severity": "NONE",
                "safe_to_proceed": True,
                "pairs_checked": 0,
                "current_generics": [],
                "history_generics": [],
                "prior_visit_generics": [],
            }

        history = await memory_service.get_medications_for_patient(tool_context.user_id)
        result = compute_prescription_safety(current, history)
        logger.info(
            "Safety check for patient %s: %d generic(s), %d prior generic(s) in memory, "
            "%d pair(s) checked, %d interaction(s) from dataset",
            tool_context.user_id,
            len(result["current_generics"]),
            len(result["prior_visit_generics"]),
            result["pairs_checked"],
            len(result["interactions"]),
        )
        return result

    return FunctionTool(check_prescription_interactions)
