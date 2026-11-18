"""Legacy profile text parser (M3 seventh slice, skeleton).

Parses the legacy ``profiles/*.txt`` sectioned notes into structured rule
**candidates**. This module is deliberately read-only: it never writes to the
rule store, calls ComfyUI/Ollama, or guesses a value that the source marked
missing.

Source note -> provenance / confidence mapping (conservative, aligned with the
legacy confidence notes):

  * ``[已核实]`` / ``[镜像核实]`` -> verified source, ``partial`` confidence
    (identity/digest verified; author parameters may still be missing).
  * ``[作者说明]`` / ``[作者推荐]`` / ``[作者示例]`` -> author source,
    ``authoritative`` only when phrased as an explicit recommendation/example;
    otherwise ``partial``.
  * ``社区`` / ``社区经验`` / ``社区参考`` -> community source,
    ``unverified`` confidence.
  * ``未给出`` / ``待填写`` / ``（暂无…）`` / empty -> field unknown; no
    candidate rule is emitted for it.

A candidate carries the raw text value plus its mapped provenance, confidence,
the section it came from, and the original bracket note so a later import/audit
slice can review before persisting anything.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Sections recognized in the legacy profile text.
SECTIONS = (
    "IDENTITY",
    "ARCHITECTURE",
    "PROMPT STYLE",
    "GENERATION SETTINGS",
    "MODEL BEHAVIOR",
    "LOCAL WORKFLOW",
    "LOCAL TEST FEEDBACK",
    "CONFIDENCE",
)

# Missing-value markers; any field whose value matches one is treated unknown.
MISSING_MARKERS = ("未给出", "待填写", "未找到", "暂无", "no", "none", "")

_BRACKET_NOTE = re.compile(r"\[([^\]]+)\]")

# Leading source labels that appear without square brackets in legacy notes.
_PREFIX_NOTES = (
    "作者推荐",
    "作者示例",
    "作者说明",
    "已核实",
    "镜像核实",
    "社区参考",
    "社区经验",
    "待核实",
)


@dataclass(frozen=True)
class RuleCandidate:
    section: str
    key: str
    value: str
    provenance: str
    confidence: str
    note: str
    raw: str


@dataclass(frozen=True)
class ParsedProfile:
    filename: str | None
    display_name: str | None
    architecture: str | None
    candidates: list[RuleCandidate] = field(default_factory=list)
    unknown_fields: list[str] = field(default_factory=list)
    raw_sections: dict[str, dict[str, str]] = field(default_factory=dict)


def _classify(note: str) -> tuple[str, str]:
    """Map a bracket note to (provenance, confidence)."""
    text = note.strip().lower()
    if text in ("已核实", "镜像核实"):
        return "verified_mirror", "partial"
    if text in ("作者说明", "作者推荐", "作者示例"):
        return "author", "authoritative" if text in ("作者推荐", "作者示例") else "partial"
    if "社区" in text:
        return "community", "unverified"
    if text in ("待核实", "unverified"):
        return "unverified", "unverified"
    return "unverified", "unverified"


def _is_missing(value: str, field_name: str = "") -> bool:
    stripped = value.strip()
    if not stripped:
        return True
    lowered = stripped.lower()
    markers = (marker for marker in MISSING_MARKERS if marker)
    if any(lowered.startswith(marker) for marker in markers):
        return True
    # Example fields with an embedded "未找到/未给出" sentence still carry no
    # usable value; treat them missing rather than promoting the prose to a rule.
    if "example" in field_name.lower() and any(
        marker in lowered for marker in ("未找到", "未给出", "暂无")
    ):
        return True
    return False


_FULL_PAREN = re.compile(r"（[^）]*）")


def _strip_trailing_parens(value: str) -> str:
    cleaned = _FULL_PAREN.sub("", value)
    cleaned = _BRACKET_NOTE.sub("", cleaned)
    return cleaned.strip(" （）()；;，,")


def _split_note(value: str) -> tuple[str, str, str]:
    """Return (clean_value, note, remainder) for one field line.

    Recognizes both bracketed notes (``[作者推荐]``) and leading plain labels
    (``社区参考 20~30 步``).
    """
    match = _BRACKET_NOTE.search(value)
    if match:
        note = match.group(1).strip()
        cleaned = _BRACKET_NOTE.sub("", value).strip(" ；;，,")
        return cleaned, note, cleaned

    for label in _PREFIX_NOTES:
        if value.strip().startswith(label):
            cleaned = value.strip()[len(label):].strip(" ：:；;，,")
            return cleaned, label, cleaned

    return value.strip(), "", value.strip()


def parse_profile_text(text: str, source_filename: str | None = None) -> ParsedProfile:
    """Parse one legacy profile document into rule candidates.

    Unknown/missing fields are recorded in ``unknown_fields`` and produce no
    candidate. Identity filename/display/architecture are extracted at the
    top level for later matching.
    """
    sections: dict[str, dict[str, str]] = {}
    current: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1].strip()
            sections.setdefault(current, {})
            continue
        if current is None or ":" not in line:
            continue
        field_name, raw_value = line.split(":", 1)
        sections.setdefault(current, {})[field_name.strip()] = raw_value.strip()

    candidates: list[RuleCandidate] = []
    unknown_fields: list[str] = []
    filename: str | None = None
    display_name: str | None = None
    architecture: str | None = None

    for section, fields in sections.items():
        for field_name, raw_value in fields.items():
            clean, note, remainder = _split_note(raw_value)

            if section == "IDENTITY":
                if field_name == "Exact Checkpoint Filename":
                    filename = clean or None
                elif field_name == "Display Name":
                    display_name = clean or None

            if section == "ARCHITECTURE" and field_name == "Base Architecture":
                # Strip trailing parenthetical provenance notes such as
                # "SD1.5（SHA256 一致）" so the architecture stays a clean label.
                architecture = _strip_trailing_parens(clean) or None

            if _is_missing(clean, field_name):
                unknown_fields.append(f"{section}::{field_name}")
                continue

            provenance, confidence = _classify(note)
            candidates.append(
                RuleCandidate(
                    section=section,
                    key=field_name,
                    value=remainder,
                    provenance=provenance,
                    confidence=confidence,
                    note=note,
                    raw=raw_value,
                )
            )

    return ParsedProfile(
        filename=filename,
        display_name=display_name,
        architecture=architecture,
        candidates=candidates,
        unknown_fields=unknown_fields,
        raw_sections=sections,
    )


def candidates_to_records(
    profile: ParsedProfile,
    level: str,
    scope_key: str | None,
) -> list[dict[str, Any]]:
    """Project candidates onto the rule record shape for later review/import.

    This returns plain dictionaries only; persistence remains a separate slice.
    """
    records: list[dict[str, Any]] = []
    for candidate in profile.candidates:
        records.append(
            {
                "level": level,
                "scope_key": scope_key,
                "rule_key": f"{candidate.section}::{candidate.key}",
                "value": candidate.value,
                "provenance": candidate.provenance,
                "confidence": candidate.confidence,
                "version": "legacy-1",
                "note": candidate.note,
                "source_section": candidate.section,
                "source_raw": candidate.raw,
            }
        )
    return records
