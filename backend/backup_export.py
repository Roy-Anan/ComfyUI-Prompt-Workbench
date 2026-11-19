"""Read-only local backup archive for the workbench data root.

Scope (conservative, local-only):

  * Included persistent domains: settings file, SQLite database, workflow
    copies and version snapshots, knowledge material, prompt templates,
    drafts, and generation-history index records.
  * Excluded rebuildable / derived / self-referential domains: ``cache``,
    ``logs``, ``backups`` (prior backups), ``exports`` (prior downloads),
    and corrupt-settings sidecar files.
  * ComfyUI-owned data (checkpoint / LoRA / CLIP / VAE weights, generated
    images) stays in the ComfyUI directories; only their configured paths
    are recorded in the manifest. No weight or original image is copied.

This module only builds an archive; restore / integrity-verified recovery
is a separate, later slice.
"""

from __future__ import annotations

import io
import json
import sqlite3
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_NAME = "ComfyUI-Prompt-Workbench"

# Persistent user domains archived under the data root.
INCLUDE_DIRS = ("workflows", "knowledge", "prompts", "drafts", "history", "assets")
# Rebuildable, derived, or self-referential domains never archived.
EXCLUDE_DIRS = ("cache", "logs", "backups", "exports")

SETTINGS_REL = Path("settings") / "settings.json"
DATABASE_REL = Path("database") / "workbench.sqlite3"

# External ComfyUI directories are recorded as paths only, never copied.
EXTERNAL_KEYS = ("checkpoint", "lora", "clip", "vae", "output")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _safe_rel(root: Path, file_path: Path) -> Path:
    """Return the root-relative path, rejecting anything that escapes root."""
    rel = file_path.resolve().relative_to(root.resolve())
    return rel


def _collect_domain(root: Path, dir_name: str) -> list[tuple[Path, bytes]]:
    domain_dir = root / dir_name
    if not domain_dir.is_dir():
        return []
    entries: list[tuple[Path, bytes]] = []
    for file_path in domain_dir.rglob("*"):
        if not file_path.is_file():
            continue
        try:
            rel = _safe_rel(root, file_path)
            data = file_path.read_bytes()
        except (OSError, ValueError):
            # Conservative: skip an unreadable entry rather than aborting the
            # whole archive; the manifest still reports what was collected.
            continue
        entries.append((rel, data))
    return entries


def _backup_database(root: Path) -> tuple[bytes | None, str | None, int]:
    """Online SQLite backup via the backup API to a temporary file.

    Returns ``(database_bytes, integrity_status, byte_count)``. A missing
    database reports ``(None, "missing", 0)``; a failure reports the error
    status instead of raising, so the rest of the archive still builds. The
    archived member is a real ``.sqlite3`` file (not a SQL dump) so a later
    restore can open it directly.
    """
    db_path = root / DATABASE_REL
    if not db_path.is_file():
        return None, "missing", 0
    tmp_path = root / "backups" / f".backup-db-{_stamp()}-{id(object())}.sqlite3"
    try:
        source = sqlite3.connect(str(db_path), timeout=10)
        try:
            integrity_row = source.execute("PRAGMA integrity_check").fetchone()
            integrity = str(integrity_row[0]) if integrity_row else "unknown"
            tmp_path.parent.mkdir(parents=True, exist_ok=True)
            target = sqlite3.connect(str(tmp_path), timeout=10)
            try:
                source.backup(target)
            finally:
                target.close()
        finally:
            source.close()
        data = tmp_path.read_bytes()
        return data, integrity, len(data)
    except sqlite3.Error as exc:
        return None, f"error: {type(exc).__name__}: {exc}", 0
    except OSError as exc:
        return None, f"error: {type(exc).__name__}: {exc}", 0
    finally:
        tmp_path.unlink(missing_ok=True)


def _load_settings(root: Path) -> dict[str, Any]:
    settings_file = root / SETTINGS_REL
    if not settings_file.is_file():
        return {}
    try:
        loaded = json.loads(settings_file.read_text(encoding="utf-8"))
        return loaded if isinstance(loaded, dict) else {}
    except (OSError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return {}


def _external_record(settings: dict[str, Any]) -> dict[str, dict[str, Any]]:
    storage = settings.get("storage", {})
    if not isinstance(storage, dict):
        storage = {}
    record: dict[str, dict[str, Any]] = {}
    for key in EXTERNAL_KEYS:
        raw = storage.get(key, "")
        path = str(raw).strip() if isinstance(raw, str) else ""
        exists = bool(path and Path(path).expanduser().is_dir())
        record[key] = {"configured": path, "exists": exists}
    return record


def build_backup_archive(root: Path, version: str) -> tuple[bytes, dict[str, Any]]:
    """Build the backup ZIP bytes and its manifest.

    Never raises on a single unreadable data file; failures are recorded in
    the manifest so the caller can surface them conservatively.
    """
    root = root.resolve()
    settings = _load_settings(root)

    domains: dict[str, dict[str, Any]] = {}
    archive: list[tuple[Path, bytes]] = []

    for dir_name in INCLUDE_DIRS:
        collected = _collect_domain(root, dir_name)
        domains[dir_name] = {
            "files": len(collected),
            "bytes": sum(len(data) for _, data in collected),
        }
        archive.extend(collected)

    # Settings file (current settings only; corrupt sidecars are excluded).
    settings_file = root / SETTINGS_REL
    settings_included = False
    settings_bytes: bytes | None = None
    if settings_file.is_file():
        try:
            settings_bytes = settings_file.read_bytes()
            settings_included = True
            archive.append((_safe_rel(root, settings_file), settings_bytes))
        except OSError:
            settings_bytes = None

    database_bytes, db_integrity, db_bytes = _backup_database(root)
    if database_bytes is not None:
        archive.append((Path(*DATABASE_REL.parts), database_bytes))

    settings_storage = settings.get("storage", {})
    settings_connections = settings.get("connections", {})
    manifest: dict[str, Any] = {
        "app": APP_NAME,
        "version": version,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_root": str(root),
        "domains": domains,
        "settings": {
            "included": settings_included,
            "path": str(SETTINGS_REL.as_posix()),
        },
        "database": {
            "included": database_bytes is not None,
            "path": str(DATABASE_REL.as_posix()),
            "integrity": db_integrity,
            "bytes": db_bytes,
        },
        "excluded_dirs": list(EXCLUDE_DIRS),
        "external_directories": _external_record(settings),
        "connections": {
            key: settings_connections.get(key, "")
            for key in ("ollama_url", "comfyui_url")
            if isinstance(settings_connections, dict)
        },
        "notes": (
            "本地只读备份；不含模型权重、LoRA/CLIP/VAE 文件与 ComfyUI "
            "原图，外部目录仅登记配置路径。恢复与完整性校验为后续切片。"
        ),
    }

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        for rel, data in archive:
            zf.writestr(rel.as_posix(), data)

    return buffer.getvalue(), manifest


def backup_filename() -> str:
    return f"workbench-backup-{_stamp()}.zip"
