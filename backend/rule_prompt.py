"""Assemble a trimmed, LLM-ready rule prompt payload (M3 thirteenth slice).

R17 already returns only the rules relevant to one workflow checkpoint. This
layer turns that context into a payload that can be handed to a local model:

  * every field is resolved through the engine's programmatic
    checkpoint -> architecture -> global inheritance;
  * the winning source level, provenance, confidence and version are kept so
    the downstream model can audit where a fact came from;
  * same-level disagreements stay marked ``conflict`` and uncovered fields stay
    ``unknown``; the model is never asked to guess a value or a priority;
  * unrelated stored rules are not copied into the payload.

This slice builds the payload only. It does not call Ollama, send a prompt,
or write back to any workflow.
"""

from __future__ import annotations

from typing import Any

import rule_engine


def _record_to_engine(row: dict[str, Any]) -> rule_engine.RuleRecord:
    return rule_engine.RuleRecord(
        level=row["level"],
        scope_key=row["scope_key"] or None,
        key=row["rule_key"],
        value=row["value"],
        provenance=row["provenance"],
        confidence=row["confidence"],
        version=row["version"],
        note=row["note"],
    )


def _field_entry(resolution: dict[str, Any], structured: Any = None) -> dict[str, Any]:
    """Normalize one engine resolution into a prompt-payload field entry."""
    entry: dict[str, Any] = {
        "key": resolution["key"],
        "status": resolution["status"],
        "value": resolution.get("value"),
        "structured": structured,
        "source_level": resolution.get("source_level"),
    }
    if resolution["status"] == "resolved":
        entry["source"] = resolution.get("source")
    elif resolution["status"] == "conflict":
        entry["sources"] = resolution.get("sources")
        entry["message"] = resolution.get("message")
    return entry


def _record_key(record: rule_engine.RuleRecord) -> str:
    return record.key


def build_prompt_context(context: dict[str, Any]) -> dict[str, Any]:
    """Build the trimmed prompt payload from a R17 rule context.

    ``context`` is the dict returned by ``rule_store.context_for_checkpoint``.
    The returned payload carries the resolved fields, the conflict/unknown
    lists, and a short human-readable instruction block. For an unregistered
    checkpoint the payload reports that status and an empty field list; it
    never fabricates a rule.
    """
    checkpoint = context.get("checkpoint")
    architecture = context.get("architecture")
    architecture_family = context.get("architecture_family")
    architecture_label = context.get("architecture_label")
    status = context.get("status", "unregistered")

    checkpoint_rules = context.get("checkpoint_rules", [])
    architecture_rules = context.get("architecture_rules", [])
    global_rules = context.get("global_rules", [])

    if status != "registered":
        return {
            "status": status,
            "checkpoint": checkpoint,
            "architecture": architecture,
            "architecture_family": architecture_family,
            "architecture_label": architecture_label,
            "fields": [],
            "conflicts": [],
            "unknown": [],
            "instruction": "当前工作流未在规则库登记；不得依据模型名猜测参数或风格，按工作流现有内容处理。",
        }

    engine_records = [
        _record_to_engine(row)
        for row in checkpoint_rules + architecture_rules + global_rules
    ]
    structured_by_key = {
        row["rule_key"]: row.get("structured")
        for row in checkpoint_rules + architecture_rules + global_rules
    }
    keys = sorted({_record_key(record) for record in engine_records})

    resolved = rule_engine.resolve_context(
        engine_records, "checkpoint", checkpoint, keys, architecture_scope=architecture
    )
    fields = [
        _field_entry(resolved["fields"][key], structured_by_key.get(key))
        for key in keys
    ]

    return {
        "status": "registered",
        "checkpoint": checkpoint,
        "architecture": architecture,
        "architecture_family": architecture_family,
        "architecture_label": architecture_label,
        "fields": fields,
        "conflicts": resolved["conflicts"],
        "unknown": resolved["unknown"],
        "instruction": (
            "仅采用下列经程序继承解析的规则；checkpoint 规则优先于架构规则，"
            "架构规则优先于全局规则。标注 conflict 的字段需人工核对，标注 unknown "
            "的字段不要补默认值；来源与可信度随字段保留。"
        ),
    }
