"""Persistent rule store (M3 fifth slice, skeleton).

Stores structured rule records in the workbench SQLite database and loads them
into :mod:`rule_engine` :class:`RuleRecord` objects for inheritance resolution.

Scope kept narrow here:
  * one row per (level, scope_key, key); upsert replaces that exact triple;
  * value is stored as JSON so scalar/list/object facts survive a round trip;
  * lookup helpers return plain dictionaries for the API;
  * no import from legacy profile text, no LLM context assembly yet.

Conflict detection, multi-model/LoRA combination, human adjudication and
dynamic retrieval remain later slices.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

import architecture_normalize
import rule_engine

_SCHEMA = """
CREATE TABLE IF NOT EXISTS workbench_rule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level TEXT NOT NULL,
    scope_key TEXT NOT NULL,
    rule_key TEXT NOT NULL,
    value_json TEXT NOT NULL,
    structured_json TEXT,
    provenance TEXT NOT NULL,
    confidence TEXT NOT NULL,
    version TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(level, scope_key, rule_key)
);
CREATE INDEX IF NOT EXISTS idx_workbench_rule_scope
    ON workbench_rule(level, scope_key);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(_SCHEMA)
    # Backfill the structured column for databases created before R15.
    columns = {row[1] for row in connection.execute("PRAGMA table_info(workbench_rule)")}
    if "structured_json" not in columns:
        connection.execute("ALTER TABLE workbench_rule ADD COLUMN structured_json TEXT")
    connection.commit()


def _encode_value(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _decode_value(raw: str) -> Any:
    return json.loads(raw)


def _row_to_record(row: sqlite3.Row | tuple[Any, ...]) -> dict[str, Any]:
    keys = (
        "id",
        "level",
        "scope_key",
        "rule_key",
        "value_json",
        "structured_json",
        "provenance",
        "confidence",
        "version",
        "note",
        "created_at",
        "updated_at",
    )
    record = dict(zip(keys, row))
    record["value"] = _decode_value(record.pop("value_json"))
    structured_raw = record.pop("structured_json")
    record["structured"] = _decode_value(structured_raw) if structured_raw else None
    return record


def upsert_rule(
    connection: sqlite3.Connection,
    level: str,
    scope_key: str | None,
    rule_key: str,
    value: Any,
    provenance: str = "unverified",
    confidence: str = "unverified",
    version: str = "1",
    note: str = "",
    structured: Any = None,
) -> dict[str, Any]:
    """Insert or replace one rule identified by level/scope_key/key."""
    probe = rule_engine.RuleRecord(
        level=level,
        scope_key=scope_key,
        key=rule_key,
        value=value,
        provenance=provenance,
        confidence=confidence,
        version=version,
        note=note,
    )
    probe.validate()

    effective_scope = scope_key or ""
    now = _now()
    structured_json = _encode_value(structured) if structured is not None else None
    connection.execute(
        """
        INSERT INTO workbench_rule
            (level, scope_key, rule_key, value_json, structured_json,
             provenance, confidence, version, note, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(level, scope_key, rule_key) DO UPDATE SET
            value_json = excluded.value_json,
            structured_json = excluded.structured_json,
            provenance = excluded.provenance,
            confidence = excluded.confidence,
            version = excluded.version,
            note = excluded.note,
            updated_at = excluded.updated_at
        """,
        (
            level,
            effective_scope,
            rule_key,
            _encode_value(value),
            structured_json,
            provenance,
            confidence,
            version,
            note,
            now,
            now,
        ),
    )
    connection.commit()
    return lookup_rule(connection, level, effective_scope, rule_key)


def lookup_rule(
    connection: sqlite3.Connection, level: str, scope_key: str, rule_key: str
) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT id, level, scope_key, rule_key, value_json, structured_json,
               provenance, confidence, version, note, created_at, updated_at
        FROM workbench_rule
        WHERE level = ? AND scope_key = ? AND rule_key = ?
        """,
        (level, scope_key or "", rule_key),
    ).fetchone()
    return _row_to_record(row) if row else None


def list_rules(
    connection: sqlite3.Connection, level: str | None = None, scope_key: str | None = None
) -> list[dict[str, Any]]:
    sql = (
        "SELECT id, level, scope_key, rule_key, value_json, structured_json, "
        "provenance, confidence, version, note, created_at, updated_at FROM workbench_rule"
    )
    clauses: list[str] = []
    params: list[Any] = []
    if level is not None:
        clauses.append("level = ?")
        params.append(level)
    if scope_key is not None:
        clauses.append("scope_key = ?")
        params.append(scope_key)
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY level, scope_key, rule_key"
    rows = connection.execute(sql, params).fetchall()
    return [_row_to_record(row) for row in rows]


def delete_rule(
    connection: sqlite3.Connection, level: str, scope_key: str, rule_key: str
) -> bool:
    cursor = connection.execute(
        """
        DELETE FROM workbench_rule
        WHERE level = ? AND scope_key = ? AND rule_key = ?
        """,
        (level, scope_key or "", rule_key),
    )
    connection.commit()
    return cursor.rowcount > 0


def load_records(
    connection: sqlite3.Connection,
) -> list[rule_engine.RuleRecord]:
    """Load every stored rule as engine records for resolution."""
    records: list[rule_engine.RuleRecord] = []
    for row in list_rules(connection):
        records.append(
            rule_engine.RuleRecord(
                level=row["level"],
                scope_key=row["scope_key"] or None,
                key=row["rule_key"],
                value=row["value"],
                provenance=row["provenance"],
                confidence=row["confidence"],
                version=row["version"],
                note=row["note"],
            )
        )
    return records


def resolve_stored(
    connection: sqlite3.Connection,
    level: str,
    scope_key: str | None,
    keys: list[str],
) -> dict[str, Any]:
    """Resolve requested keys against stored rules via the engine."""
    records = load_records(connection)
    return rule_engine.resolve_context(records, level, scope_key, keys)


def _architecture_label(records: list[dict[str, Any]], checkpoint: str) -> str | None:
    """Extract the raw Base Architecture fact for one checkpoint, if stored.

    Prefers the checkpoint-scoped ``IDENTITY::Base Architecture`` pointer
    written on import; falls back to the architecture bucket only for legacy
    databases that predate that pointer, and never guesses a family across a
    different checkpoint.
    """
    checkpoint_keys = ("IDENTITY::Base Architecture", "ARCHITECTURE::Base Architecture")
    for rule_key in checkpoint_keys:
        base_record = next(
            (
                row for row in records
                if row["level"] == "checkpoint"
                and row["scope_key"] == checkpoint
                and row["rule_key"] == rule_key
            ),
            None,
        )
        if base_record is not None:
            label = str(base_record["value"]).strip()
            return label or None

    # Legacy fallback: the family pointer lived only in the architecture
    # bucket. Only use it when a single architecture scope stores the fact;
    # with multiple families present there, do not pick one at random.
    arch_facts = [
        row for row in records
        if row["level"] == "architecture"
        and row["rule_key"] == "ARCHITECTURE::Base Architecture"
    ]
    if len(arch_facts) == 1:
        label = str(arch_facts[0]["value"]).strip()
        return label or None
    return None


def _architecture_scope_matches(scope: str | None, label: str | None) -> bool:
    """True when an architecture scope belongs to the checkpoint's family.

    Same-family match goes through :mod:`architecture_normalize` so variants
    such as ``SDXL`` and ``SDXL 1.0`` inherit each other's rules. When either
    side is unrecognized, fall back to the conservative exact / prefix /
    substring comparison; mixed or derived labels are not merged into a plain
    family by this check.
    """
    if not scope or not label:
        return False
    label_norm = architecture_normalize.normalize(label)
    scope_norm = architecture_normalize.normalize(scope)
    # When both sides are recognized, match strictly by canonical family;
    # a mixed/derived label is never merged into a plain family by substring.
    if label_norm["matched"] and scope_norm["matched"]:
        return label_norm["canonical"] == scope_norm["canonical"]
    # Only one side recognized: conservative, do not guess a family.
    if label_norm["matched"] or scope_norm["matched"]:
        return False
    return label == scope or label.startswith(scope) or scope in label


def _checkpoint_architecture(
    records: list[dict[str, Any]],
    checkpoint: str,
    label: str | None = None,
) -> str | None:
    """Find the architecture scope that matches one checkpoint's family."""
    arch_scopes = {
        row["scope_key"]
        for row in records
        if row["level"] == "architecture" and row["scope_key"]
    }
    if not arch_scopes:
        return None
    if label is None:
        label = _architecture_label(records, checkpoint)
    if label is None:
        return None
    for scope in arch_scopes:
        if _architecture_scope_matches(scope, label):
            return scope
    return None


def context_for_checkpoint(
    connection: sqlite3.Connection,
    checkpoint: str,
) -> dict[str, Any]:
    """Assemble the relevant stored rules for one checkpoint workflow context.

    Returns the checkpoint record set, the matched architecture scope (or None)
    and all global rules. Only rules relevant to this context are returned;
    unrelated stored rules are never surfaced. A checkpoint with no stored rule
    at all is reported ``unregistered`` and carries an empty rule set, matching
    the legacy exact-match / no-fabrication policy.
    """
    records = list_rules(connection)
    checkpoint_rules = [row for row in records if row["level"] == "checkpoint" and row["scope_key"] == checkpoint]
    registered = bool(checkpoint_rules)

    # An unregistered checkpoint must not inherit an arbitrary architecture
    # label from another model's architecture bucket; leave the family unset.
    arch_label = _architecture_label(records, checkpoint) if registered else None
    architecture = _checkpoint_architecture(records, checkpoint, arch_label)
    arch_norm = architecture_normalize.normalize(arch_label)
    architecture_rules = [
        row for row in records
        if row["level"] == "architecture" and _architecture_scope_matches(row["scope_key"], arch_label)
    ]
    global_rules = [row for row in records if row["level"] == "global"]

    return {
        "status": "registered" if registered else "unregistered",
        "checkpoint": checkpoint,
        "architecture": architecture,
        "architecture_label": arch_label,
        "architecture_family": arch_norm["canonical"],
        "checkpoint_rules": checkpoint_rules,
        "architecture_rules": architecture_rules,
        "global_rules": global_rules,
    }
