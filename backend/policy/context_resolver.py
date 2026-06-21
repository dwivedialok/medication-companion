"""
backend/policy/context_resolver.py
ContextResolver (Day 5 §3.3).

Resolves `[[PLACEHOLDER]]` tokens in agent instructions against a typed
RenderContext sourced from specs/schemas/language_map.yaml. Fail-closed:
unresolved tokens raise ContextResolverError so prompts never reach the
model with literal `[[VARS]]`.

Used by Agent 5 (localisation) — see agents/agent5_localisation.py — and
documented in specs/schemas/language_map.yaml under context_resolver_placeholders.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


_LANGUAGE_MAP_PATH = (
    Path(__file__).resolve().parents[2] / "specs" / "schemas" / "language_map.yaml"
)
_PLACEHOLDER_RE = re.compile(r"\[\[([A-Z_][A-Z0-9_]*)\]\]")
_DEFAULT_LANGUAGE = "en-IN"
_VALID_SEVERITIES = {"HIGH", "MODERATE", "LOW", "INFO", "NONE"}


class ContextResolverError(ValueError):
    """Raised when a template contains unresolved or unsafe placeholders."""


@dataclass(frozen=True)
class RenderContext:
    """Typed inputs for the resolver. Anything optional must have a default
    in language_map.yaml so we never substitute None into the prompt."""

    patient_language: str = _DEFAULT_LANGUAGE
    overall_severity: str = "INFO"
    patient_given_name: str | None = None
    extra: dict[str, str] = field(default_factory=dict)

    def validated(self) -> "RenderContext":
        sev = (self.overall_severity or "INFO").upper()
        if sev not in _VALID_SEVERITIES:
            raise ContextResolverError(
                f"overall_severity must be one of {_VALID_SEVERITIES}, got {sev!r}"
            )
        lang = self.patient_language or _DEFAULT_LANGUAGE
        return RenderContext(
            patient_language=lang,
            overall_severity=sev,
            patient_given_name=self.patient_given_name,
            extra=dict(self.extra),
        )


def _load_language_map() -> dict[str, Any]:
    with _LANGUAGE_MAP_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


_LANGUAGE_MAP = _load_language_map()


def _language_entry(code: str) -> dict[str, Any]:
    languages = _LANGUAGE_MAP.get("supported_languages", {})
    entry = languages.get(code) or languages.get(_DEFAULT_LANGUAGE)
    if entry is None:
        raise ContextResolverError(
            f"language_map.yaml has no entry for {code!r} or the default {_DEFAULT_LANGUAGE!r}"
        )
    return entry


class ContextResolver:
    """Substitute `[[PLACEHOLDER]]` tokens with values from RenderContext +
    language_map.yaml. Stateless and idempotent."""

    BUILTIN_KEYS = {
        "PATIENT_LANGUAGE",
        "SEVERITY_TONE",
        "DISCLAIMER",
        "PATIENT_GIVEN_NAME",
        "TTS_VOICE",
    }

    def resolve(self, template: str, context: RenderContext) -> str:
        ctx = context.validated()
        entry = _language_entry(ctx.patient_language)

        resolved_values: dict[str, str] = {
            "PATIENT_LANGUAGE": ctx.patient_language,
            "SEVERITY_TONE": entry["severity_tone_phrases"][ctx.overall_severity],
            "DISCLAIMER": entry["disclaimer_translation"].strip(),
            "TTS_VOICE": entry["tts_voice"],
            "PATIENT_GIVEN_NAME": ctx.patient_given_name or "",
        }
        resolved_values.update(ctx.extra or {})

        def _sub(match: re.Match[str]) -> str:
            key = match.group(1)
            if key not in resolved_values:
                raise ContextResolverError(
                    f"Unknown placeholder [[{key}]] — not in RenderContext or language_map"
                )
            value = resolved_values[key]
            if value is None:
                raise ContextResolverError(
                    f"Placeholder [[{key}]] resolved to None (fail-closed)"
                )
            return str(value)

        rendered = _PLACEHOLDER_RE.sub(_sub, template)

        if _PLACEHOLDER_RE.search(rendered):
            raise ContextResolverError(
                "Template still contains placeholders after resolve — fail-closed"
            )

        return rendered

    def disclaimer_for(self, language_code: str) -> str:
        return _language_entry(language_code)["disclaimer_translation"].strip()

    def tone_for(self, language_code: str, severity: str) -> str:
        return _language_entry(language_code)["severity_tone_phrases"][severity.upper()]
