"""Rule engine skeleton (M3 fourth slice).

Defines the structured rule record and a programmatic inheritance resolution
for three levels: ``checkpoint`` > ``architecture`` > ``global``.

Design constraints carried from the project safety rules:

  * Inheritance priority is decided by the program, never guessed by an LLM.
  * When two rules at the **same** level disagree on the same key, the field is
    marked ``conflict`` instead of picking one value; conflicts are not
    silently resolved here.
  * A field covered at no level resolves to ``unknown``; the engine never
    fabricates a default.
  * Every resolved value keeps its source level, provenance label, confidence
    and version so later slices can audit where a rule came from.

This slice is a pure resolution layer: it does not read the filesystem, call
ComfyUI/Ollama, or write back to any workflow. Rule storage/import, dynamic
retrieval and LLM context assembly are later slices.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Inheritance levels, ordered from most specific to most general.
LEVEL_ORDER = ("checkpoint", "architecture", "global")

# Provenance labels kept aligned with the legacy profile confidence notes.
VALID_PROVENANCE = ("author", "verified_mirror", "community", "local_test", "unverified")

VALID_CONFIDENCE = ("authoritative", "partial", "unverified")

# Levels that participate in per-level conflict detection.
LEVEL_RANK = {level: index for index, level in enumerate(LEVEL_ORDER)}


class RuleError(ValueError):
    """A rule record or request is structurally invalid."""


@dataclass(frozen=True)
class RuleRecord:
    """One structured rule fact attached to a scope level.

    ``scope_key`` identifies the specific entity at that level, e.g. a
    checkpoint filename or an architecture id; ignored for ``global``.
    """

    level: str
    scope_key: str | None
    key: str
    value: Any
    provenance: str = "unverified"
    confidence: str = "unverified"
    version: str = "1"
    note: str = ""

    def validate(self) -> None:
        if self.level not in LEVEL_RANK:
            raise RuleError(f"Unknown rule level: {self.level}")
        if not self.key or not isinstance(self.key, str):
            raise RuleError("Rule key must be a non-empty string")
        if self.level != "global" and not self.scope_key:
            raise RuleError(f"{self.level} rule requires a scope_key")
        if self.provenance not in VALID_PROVENANCE:
            raise RuleError(f"Unknown provenance: {self.provenance}")
        if self.confidence not in VALID_CONFIDENCE:
            raise RuleError(f"Unknown confidence: {self.confidence}")


def _index_by_level(
    rules: list[RuleRecord],
) -> dict[str, dict[str, list[RuleRecord]]]:
    """Group rules as ``level -> scope_key -> key -> records``."""
    indexed: dict[str, dict[str, list[RuleRecord]]] = {
        level: {} for level in LEVEL_ORDER
    }
    for record in rules:
        record.validate()
        bucket = indexed[record.level].setdefault(record.scope_key or "", [])
        bucket.append(record)
    return indexed


def _same_level_conflict(records: list[RuleRecord]) -> bool:
    """True when records at one level disagree on the field value."""
    values = {repr(record.value) for record in records}
    return len(values) > 1


def resolve_field(
    rules: list[RuleRecord],
    level: str,
    scope_key: str | None,
    key: str,
) -> dict[str, Any]:
    """Resolve one field for a checkpoint/architecture context.

    Search order: checkpoint scope -> architecture scope -> global. The first
    level that covers the key wins (programmatic priority). A same-level value
    disagreement resolves to ``conflict``; an uncovered field resolves to
    ``unknown``.
    """
    if level not in LEVEL_RANK:
        raise RuleError(f"Unknown context level: {level}")

    indexed = _index_by_level(rules)
    context_scopes: list[tuple[str, str | None]] = [
        ("checkpoint", scope_key),
        ("architecture", scope_key if level == "architecture" else None),
        ("global", None),
    ]
    # When the request itself targets architecture, do not let a checkpoint
    # scope shadow it; checkpoint inheritance only applies to checkpoint ctx.
    if level == "architecture":
        context_scopes = [
            ("architecture", scope_key),
            ("global", None),
        ]

    for rule_level, rule_scope in context_scopes:
        if rule_scope is None and rule_level != "global":
            continue
        scope_bucket = indexed[rule_level].get(rule_scope or "", [])
        matches = [record for record in scope_bucket if record.key == key]
        if not matches:
            continue

        if _same_level_conflict(matches):
            return {
                "status": "conflict",
                "key": key,
                "value": None,
                "source_level": rule_level,
                "sources": [_source(record) for record in matches],
                "message": "同一层级存在冲突规则，需人工核对后再采用",
            }

        record = matches[0]
        return {
            "status": "resolved",
            "key": key,
            "value": record.value,
            "source_level": rule_level,
            "source": _source(record),
        }

    return {"status": "unknown", "key": key, "value": None, "source_level": None}


def _source(record: RuleRecord) -> dict[str, Any]:
    return {
        "level": record.level,
        "scope_key": record.scope_key,
        "provenance": record.provenance,
        "confidence": record.confidence,
        "version": record.version,
        "note": record.note,
    }


def resolve_context(
    rules: list[RuleRecord],
    level: str,
    scope_key: str | None,
    keys: list[str],
) -> dict[str, Any]:
    """Resolve several fields for one context in a single pass.

    Returns ``{fields: {key: resolution}, conflicts: [...], unknown: [...]}``.
    Only requested keys are evaluated; unrelated rules are never sent onward.
    """
    fields: dict[str, Any] = {}
    conflicts: list[str] = []
    unknown: list[str] = []

    for key in keys:
        resolution = resolve_field(rules, level, scope_key, key)
        fields[key] = resolution
        if resolution["status"] == "conflict":
            conflicts.append(key)
        elif resolution["status"] == "unknown":
            unknown.append(key)

    return {
        "context_level": level,
        "context_scope": scope_key,
        "fields": fields,
        "conflicts": conflicts,
        "unknown": unknown,
    }


def summarize_rules(rules: list[RuleRecord]) -> dict[str, Any]:
    """Inventory of recorded rules by level (for later review surfaces)."""
    summary: dict[str, Any] = {level: {"scopes": {}, "count": 0} for level in LEVEL_ORDER}
    for record in rules:
        record.validate()
        scope = record.scope_key or ""
        entry = summary[record.level]["scopes"].setdefault(scope, {"keys": [], "count": 0})
        entry["keys"].append(record.key)
        entry["count"] += 1
        summary[record.level]["count"] += 1
    return summary
