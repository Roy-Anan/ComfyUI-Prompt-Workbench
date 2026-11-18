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

import rule_engine

_SCHEMA = """
CREATE TABLE IF NOT EXISTS workbench_rule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level TEXT NOT NULL,
    scope_key TEXT NOT NULL,
    rule_key TEXT NOT NULL,
    value_json TEXT NOT NULL,
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
        "provenance",
        "confidence",
        "version",
        "note",
        "created_at",
        "updated_at",
    )
    record = dict(zip(keys, row))
    record["value"] = _decode_value(record.pop("value_json"))
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
    connection.execute(
        """
        INSERT INTO workbench_rule
            (level, scope_key, rule_key, value_json, provenance, confidence,
             version, note, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(level, scope_key, rule_key) DO UPDATE SET
            value_json = excluded.value_json,
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
        SELECT id, level, scope_key, rule_key, value_json, provenance,
               confidence, version, note, created_at, updated_at
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
        "SELECT id, level, scope_key, rule_key, value_json, provenance, "
        "confidence, version, note, created_at, updated_at FROM workbench_rule"
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
