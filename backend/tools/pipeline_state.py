"""
backend/tools/pipeline_state.py
Deterministic session-state helpers for the prescription pipeline.

Pins Agent 1 OCR names into session state and filters Agent 2 output so
downstream agents cannot use drugs that were not read from the image.
"""
from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from google.adk.agents.callback_context import CallbackContext

from agents.agent1_reader import ExtractedDrug, ReaderOutput
from agents.agent2_resolver import ResolvedDrug, ResolverOutput
from tools.drug_normalize import normalize_brand, normalize_generic

logger = logging.getLogger(__name__)

EXTRACTED_RAW_NAMES_KEY = "extracted_raw_names"
RESOLVED_DRUGS_KEY = "resolved_drugs"
PRIOR_VISIT_GENERICS_KEY = "prior_visit_generics"

# Common Rx line prefixes/tokens — not useful alone for brand matching.
_NOISE_TOKENS = frozenset(
    {
        "tab",
        "cap",
        "capsule",
        "tablet",
        "syrup",
        "inj",
        "od",
        "bd",
        "tds",
        "hs",
        "mg",
        "ml",
    }
)


def normalized_raw_names(raw_names: list[str]) -> set[str]:
    """Normalize prescription raw names for allowlist matching."""
    keys = {normalize_brand(name) for name in raw_names if name and name.strip()}
    keys.discard("")
    return keys


def allowlist_match_keys(raw_names: list[str]) -> set[str]:
    """
    Build normalized keys for allowlist matching.

    Includes full normalized lines plus significant tokens so Agent 2 can match
    short brand names (e.g. "Ecosprin") to OCR lines ("Tab Ecosprin 75 mg").
    """
    keys: set[str] = set()
    for name in raw_names:
        if not name or not name.strip():
            continue
        normalized = normalize_brand(name)
        if not normalized:
            continue
        keys.add(normalized)
        for token in normalized.split():
            if len(token) >= 3 and token not in _NOISE_TOKENS:
                keys.add(token)
    return keys


def resolver_raw_on_allowlist(raw_name: str, allowed_raw_names: list[str]) -> bool:
    """Return True when a resolver raw_name corresponds to an extracted OCR line."""
    key = normalize_brand(raw_name)
    if not key:
        return False

    allowed = allowlist_match_keys(allowed_raw_names)
    if key in allowed:
        return True

    key_tokens = set(key.split())
    for candidate in allowed:
        if key in candidate or candidate in key:
            return True
        if key_tokens & set(candidate.split()):
            return True
    return False


def raw_names_from_reader_output(output: ReaderOutput | dict[str, Any]) -> list[str]:
    """Extract raw drug names from Agent 1 output."""
    if isinstance(output, ReaderOutput):
        drugs = output.extracted_drugs
    else:
        drugs = output.get("extracted_drugs") or []
    names: list[str] = []
    for item in drugs:
        if isinstance(item, ExtractedDrug):
            names.append(item.raw_name)
        elif isinstance(item, dict):
            raw = item.get("raw_name")
            if raw:
                names.append(str(raw))
    return names


def pin_extracted_drug_names(callback_context: CallbackContext) -> None:
    """Store Agent 1 OCR names in session state for downstream allowlisting."""
    output = callback_context.output
    if output is None:
        return

    if isinstance(output, ReaderOutput):
        reader = output
    else:
        try:
            reader = ReaderOutput.model_validate(output)
        except Exception:
            logger.warning(
                "Could not parse ReaderOutput for session %s — empty allowlist",
                callback_context.session.id,
            )
            callback_context.state[EXTRACTED_RAW_NAMES_KEY] = []
            return

    raw_names = raw_names_from_reader_output(reader)
    callback_context.state[EXTRACTED_RAW_NAMES_KEY] = raw_names
    logger.info(
        "Pinned %d extracted raw name(s) for session %s",
        len(raw_names),
        callback_context.session.id,
    )


def filter_resolver_to_allowlist(
    resolver_output: ResolverOutput | dict[str, Any],
    allowed_raw_names: list[str],
) -> ResolverOutput:
    """Drop resolved drugs whose raw_name was not extracted by Agent 1."""
    if isinstance(resolver_output, ResolverOutput):
        output = resolver_output
    else:
        output = ResolverOutput.model_validate(resolver_output)

    if not allowed_raw_names:
        if output.resolved_drugs:
            logger.warning(
                "Resolver produced %d drug(s) but Agent 1 allowlist is empty — dropping all",
                len(output.resolved_drugs),
            )
        return ResolverOutput(resolved_drugs=[], unresolved_count=output.unresolved_count)

    kept: list[ResolvedDrug] = []
    dropped = 0
    for drug in output.resolved_drugs:
        if resolver_raw_on_allowlist(drug.raw_name, allowed_raw_names):
            kept.append(drug)
        else:
            dropped += 1
            logger.warning(
                "Dropped resolver drug not on Agent 1 allowlist: raw_name=%r generic=%r",
                drug.raw_name,
                drug.generic_name,
            )

    unresolved = sum(1 for d in kept if d.tag == "UNRESOLVED")
    return ResolverOutput(resolved_drugs=kept, unresolved_count=unresolved)


def prior_generics_from_visits(visits: list[dict[str, Any]] | None) -> set[str]:
    """Collect normalized generics from prior visit records in Memory Bank."""
    generics: set[str] = set()
    for visit in visits or []:
        for name in visit.get("resolved_drugs") or []:
            generic = normalize_generic(str(name))
            if generic:
                generics.add(generic)
    return generics


def tag_resolver_against_memory(
    resolver_output: ResolverOutput,
    prior_generics: set[str],
) -> ResolverOutput:
    """Set NEW vs EXISTING from prior visit generics (deterministic, not LLM)."""
    if not prior_generics:
        return resolver_output

    tagged: list[ResolvedDrug] = []
    for drug in resolver_output.resolved_drugs:
        if drug.tag == "UNRESOLVED":
            tagged.append(drug)
            continue
        generic = normalize_generic(drug.generic_name)
        tag = "EXISTING" if generic and generic in prior_generics else "NEW"
        tagged.append(drug.model_copy(update={"tag": tag}))

    unresolved = sum(1 for drug in tagged if drug.tag == "UNRESOLVED")
    return ResolverOutput(resolved_drugs=tagged, unresolved_count=unresolved)


def resolver_output_to_state(resolver_output: ResolverOutput) -> list[dict[str, Any]]:
    """Serialize ResolverOutput for session state (memory write + safety tool)."""
    return [drug.model_dump() for drug in resolver_output.resolved_drugs]


def generics_from_resolved_state(state: Mapping[str, Any]) -> list[str]:
    """Return lowercase generic names from session state, skipping UNRESOLVED."""
    resolved = state.get(RESOLVED_DRUGS_KEY, [])
    names: list[str] = []
    for item in resolved:
        if isinstance(item, dict):
            if item.get("tag") == "UNRESOLVED":
                continue
            generic = item.get("generic_name") or item.get("generic")
        else:
            tag = getattr(item, "tag", None)
            if tag == "UNRESOLVED":
                continue
            generic = getattr(item, "generic_name", None)
        if generic:
            names.append(str(generic).lower())
    return names


async def apply_resolver_allowlist(callback_context: CallbackContext) -> None:
    """ADK after_agent_callback on Agent 2 — allowlist + NEW/EXISTING from memory."""
    output = callback_context.output
    if output is None:
        return None

    allowed = callback_context.state.get(EXTRACTED_RAW_NAMES_KEY, [])
    if isinstance(output, ResolverOutput):
        filtered = filter_resolver_to_allowlist(output, allowed)
    else:
        filtered = filter_resolver_to_allowlist(
            ResolverOutput.model_validate(output), allowed
        )

    prior_list = callback_context.state.get(PRIOR_VISIT_GENERICS_KEY, [])
    prior_generics = set(prior_list) if prior_list else set()
    if prior_generics:
        filtered = tag_resolver_against_memory(filtered, prior_generics)

    callback_context.output = filtered
    callback_context.state[RESOLVED_DRUGS_KEY] = resolver_output_to_state(filtered)
    existing_count = sum(1 for d in filtered.resolved_drugs if d.tag == "EXISTING")
    logger.info(
        "Resolver allowlist applied for session %s: kept %d drug(s), %d EXISTING",
        callback_context.session.id,
        len(filtered.resolved_drugs),
        existing_count,
    )
    return None


def create_preload_patient_memory_callback(memory_service: Any):
    """ADK before_agent_callback on Agent 2 — load Memory Bank into session state."""

    async def preload_patient_memory(callback_context: CallbackContext) -> None:
        raw_names = callback_context.state.get(EXTRACTED_RAW_NAMES_KEY, [])
        search_terms = [str(name) for name in raw_names if str(name).strip()]
        visits = await memory_service.get_medications_for_patient(
            callback_context.user_id,
            search_terms=search_terms,
        )
        prior = prior_generics_from_visits(visits)
        callback_context.state[PRIOR_VISIT_GENERICS_KEY] = sorted(prior)
        logger.info(
            "Preloaded %d prior generic(s) from %d visit(s) for patient %s",
            len(prior),
            len(visits),
            callback_context.user_id,
        )
        return None

    return preload_patient_memory


async def sync_resolver_state_for_safety(callback_context: CallbackContext) -> None:
    """
    ADK before_agent_callback on Agent 3.

    Re-populates resolved_drugs in session state when Agent 2's after_agent
    callback did not persist them (e.g. OCR line vs short brand mismatch before
    fuzzy allowlist landed, or stale session state).
    """
    if generics_from_resolved_state(callback_context.state):
        return None

    from pipeline_output import extract_agent_output

    allowed = callback_context.state.get(EXTRACTED_RAW_NAMES_KEY, [])
    if not allowed:
        reader = extract_agent_output(
            callback_context.session.events,
            agent_name="prescription_reader",
            model_cls=ReaderOutput,
            match=lambda data: "extracted_drugs" in data,
        )
        if reader is not None:
            allowed = raw_names_from_reader_output(reader)
            callback_context.state[EXTRACTED_RAW_NAMES_KEY] = allowed

    resolver = extract_agent_output(
        callback_context.session.events,
        agent_name="medication_resolver",
        model_cls=ResolverOutput,
        match=lambda data: "resolved_drugs" in data,
    )
    if resolver is None:
        logger.warning(
            "Safety pre-sync: no resolver output in session for %s",
            callback_context.session.id,
        )
        return None

    filtered = filter_resolver_to_allowlist(resolver, allowed)
    if not filtered.resolved_drugs:
        logger.warning(
            "Safety pre-sync: resolver output filtered to 0 drug(s) for session %s",
            callback_context.session.id,
        )
        return None

    prior_list = callback_context.state.get(PRIOR_VISIT_GENERICS_KEY, [])
    prior_generics = set(prior_list) if prior_list else set()
    if prior_generics:
        filtered = tag_resolver_against_memory(filtered, prior_generics)

    callback_context.state[RESOLVED_DRUGS_KEY] = resolver_output_to_state(filtered)
    logger.info(
        "Safety pre-sync wrote %d resolved drug(s) for session %s",
        len(filtered.resolved_drugs),
        callback_context.session.id,
    )
    return None
