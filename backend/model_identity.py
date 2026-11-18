"""Local model identity store (M3 second slice, skeleton).

This module records lightweight identity metadata for model weights the
workbench has seen on disk: stable path, file size, modification time and an
optional SHA256 digest. It does **not** hash every file eagerly: checkpoints
on this machine are multi-GB, so the digest is computed on demand (small LoRAs
first) and cached. A missing digest means "not hashed yet", never "unknown
hash".

Scope kept narrow here:
  * one row per on-disk model file (``category`` + ``relative_name`` +
    ``absolute_path``);
  * metadata refresh when size/mtime change;
  * optional SHA256 with a streaming reader;
  * lookup helpers used to annotate the read-only catalog.

Architecture / model / Checkpoint rule inheritance, rule provenance and
conflict detection are later M3 work and are intentionally absent.
"""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Model weight extensions recognized for identity indexing.
WEIGHT_SUFFIXES = {".safetensors", ".ckpt", ".pt", ".pth", ".bin", ".gguf"}

# Categories kept in lockstep with model_catalog groups.
CATEGORIES = ("checkpoint", "lora", "clip", "vae")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS model_identity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    relative_name TEXT NOT NULL,
    absolute_path TEXT NOT NULL,
    size_bytes INTEGER,
    mtime_ns INTEGER,
    sha256 TEXT,
    hashed_at TEXT,
    last_seen_at TEXT NOT NULL,
    UNIQUE(category, relative_name)
);
CREATE INDEX IF NOT EXISTS idx_model_identity_path
    ON model_identity(absolute_path);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path, timeout=10)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def ensure_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(_SCHEMA)
    connection.commit()


def _row_to_record(row: sqlite3.Row | tuple[Any, ...]) -> dict[str, Any]:
    keys = (
        "id",
        "category",
        "relative_name",
        "absolute_path",
        "size_bytes",
        "mtime_ns",
        "sha256",
        "hashed_at",
        "last_seen_at",
    )
    record = dict(zip(keys, row))
    record["on_disk"] = Path(record["absolute_path"]).is_file()
    return record


def _copies_with_digest(
    connection: sqlite3.Connection, category: str, digest: str
) -> list[dict[str, Any]]:
    """Other on-disk records sharing the same digest in one category."""
    rows = connection.execute(
        """
        SELECT id, category, relative_name, absolute_path, size_bytes,
               mtime_ns, sha256, hashed_at, last_seen_at
        FROM model_identity
        WHERE category = ? AND sha256 = ?
        ORDER BY absolute_path
        """,
        (category, digest),
    ).fetchall()
    return [_row_to_record(row) for row in rows]


def identity_group(
    connection: sqlite3.Connection, category: str, name: str
) -> dict[str, Any]:
    """Resolve a named file to its digest-based identity group.

    When the named file has a cached digest, every other recorded copy in the
    same category sharing that digest is listed under ``copies``; this is how
    identical weights in multiple paths map to one identity. Without a digest
    the group is unknown and no hash-based matching is inferred.
    """
    record = lookup_name(connection, category, name)
    if record is None:
        return {"known": False}

    digest = record["sha256"]
    if not digest:
        return {
            "known": True,
            "identity_key": None,
            "digest": None,
            "copies": [],
        }

    copies = _copies_with_digest(connection, category, digest)
    return {
        "known": True,
        "identity_key": f"{category}:{digest}",
        "digest": digest,
        "copies": [
            {
                "relative_name": copy["relative_name"],
                "absolute_path": copy["absolute_path"],
                "on_disk": copy["on_disk"],
                "size_bytes": copy["size_bytes"],
            }
            for copy in copies
        ],
    }


def index_directory(
    connection: sqlite3.Connection,
    category: str,
    directory: str,
) -> list[dict[str, Any]]:
    """Index weight files directly under ``directory`` for one category.

    Existing rows for the category are refreshed when size/mtime changed;
    files that disappeared are left in place but their ``on_disk`` flag is
    computed from the live filesystem at read time (no row is deleted here).
    """
    if category not in CATEGORIES:
        raise ValueError(f"Unknown model category: {category}")

    now = _now()
    path = Path(directory).expanduser() if directory else None
    indexed: dict[str, Path] = {}

    if path and path.is_dir():
        for entry in path.iterdir():
            if entry.is_file() and entry.suffix.lower() in WEIGHT_SUFFIXES:
                indexed[entry.name] = entry

    for name, entry in indexed.items():
        stat = entry.stat()
        size = stat.st_size
        mtime_ns = stat.st_mtime_ns

        existing = connection.execute(
            "SELECT absolute_path, size_bytes, mtime_ns, sha256 "
            "FROM model_identity WHERE category = ? AND relative_name = ?",
            (category, name),
        ).fetchone()

        if existing is None:
            connection.execute(
                """
                INSERT INTO model_identity
                    (category, relative_name, absolute_path, size_bytes,
                     mtime_ns, sha256, hashed_at, last_seen_at)
                VALUES (?, ?, ?, ?, ?, NULL, NULL, ?)
                """,
                (category, name, str(entry.resolve()), size, mtime_ns, now),
            )
        else:
            abs_path, old_size, old_mtime, old_hash = existing
            # Invalidate a cached digest when the file changed underneath us.
            new_hash = old_hash
            new_hashed_at = None
            if old_size != size or old_mtime != mtime_ns:
                new_hash = None
            connection.execute(
                """
                UPDATE model_identity
                SET absolute_path = ?, size_bytes = ?, mtime_ns = ?,
                    sha256 = ?, hashed_at = ?, last_seen_at = ?
                WHERE category = ? AND relative_name = ?
                """,
                (
                    str(entry.resolve()),
                    size,
                    mtime_ns,
                    new_hash,
                    new_hashed_at,
                    now,
                    category,
                    name,
                ),
            )

    connection.commit()
    return lookup_category(connection, category)


def lookup_category(
    connection: sqlite3.Connection, category: str
) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, category, relative_name, absolute_path, size_bytes,
               mtime_ns, sha256, hashed_at, last_seen_at
        FROM model_identity
        WHERE category = ?
        ORDER BY relative_name
        """,
        (category,),
    ).fetchall()
    return [_row_to_record(row) for row in rows]


def lookup_name(
    connection: sqlite3.Connection, category: str, name: str
) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT id, category, relative_name, absolute_path, size_bytes,
               mtime_ns, sha256, hashed_at, last_seen_at
        FROM model_identity
        WHERE category = ? AND relative_name = ?
        """,
        (category, name),
    ).fetchone()
    return _row_to_record(row) if row else None


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Stream a file and return its hex SHA256 (no eager full load)."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def ensure_hash(
    connection: sqlite3.Connection, category: str, name: str
) -> dict[str, Any] | None:
    """Compute and cache the SHA256 for one recorded file if missing/stale.

    Returns the updated record, or None when the name is not recorded.
    """
    record = lookup_name(connection, category, name)
    if record is None:
        return None

    path = Path(record["absolute_path"])
    if not path.is_file():
        return record

    if record["sha256"]:
        return record

    digest = sha256_file(path)
    connection.execute(
        """
        UPDATE model_identity
        SET sha256 = ?, hashed_at = ?
        WHERE category = ? AND relative_name = ?
        """,
        (digest, _now(), category, name),
    )
    connection.commit()
    return lookup_name(connection, category, name)


def identity_summary(
    connection: sqlite3.Connection, category: str, name: str
) -> dict[str, Any]:
    """Lightweight summary attached to a catalog entry.

    Returns ``{"known": False}`` when no on-disk record exists; otherwise
    reports size, on-disk state and whether a digest is cached.
    """
    record = lookup_name(connection, category, name)
    if record is None:
        return {"known": False}

    digest = record["sha256"]
    copies: list[dict[str, Any]] = []
    if digest:
        copies = [
            {
                "relative_name": copy["relative_name"],
                "absolute_path": copy["absolute_path"],
                "on_disk": copy["on_disk"],
            }
            for copy in _copies_with_digest(connection, category, digest)
        ]

    return {
        "known": True,
        "on_disk": record["on_disk"],
        "size_bytes": record["size_bytes"],
        "sha256": digest,
        "hashed": digest is not None,
        "identity_key": f"{category}:{digest}" if digest else None,
        "copy_count": len(copies),
        "copies": copies,
    }
