"""Local generation history: frozen snapshots of submitted ComfyUI tasks.

A snapshot is recorded at submission time so the Prompt text and model
selection survive later edits to the working draft. Only file names and
metadata are indexed here; original images stay under ComfyUI's own output
directory and are never copied into the workbench data root.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS generation_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_id TEXT NOT NULL UNIQUE,
    workflow_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    positive_prompt TEXT,
    negative_prompt TEXT,
    model_snapshot TEXT,
    task_status TEXT,
    images TEXT,
    last_error TEXT
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(_SCHEMA)
    connection.commit()


def _decode(raw: str | None) -> Any:
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def _row(row: sqlite3.Row | tuple[Any, ...] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    keys = [
        "id",
        "prompt_id",
        "workflow_id",
        "created_at",
        "positive_prompt",
        "negative_prompt",
        "model_snapshot",
        "task_status",
        "images",
        "last_error",
    ]
    record = dict(zip(keys, row))
    record["model_snapshot"] = _decode(record.get("model_snapshot"))
    record["images"] = _decode(record.get("images"))
    return record


def extract_prompts(working_prompts: list[dict[str, Any]]) -> dict[str, str]:
    """Split working prompt entries into positive/negative snapshot text."""
    positive: list[str] = []
    negative: list[str] = []
    for item in working_prompts or []:
        role = item.get("role")
        text = item.get("text")
        if not isinstance(text, str):
            continue
        if role == "positive" and text.strip():
            positive.append(text.strip())
        elif role == "negative" and text.strip():
            negative.append(text.strip())
    return {
        "positive": " / ".join(positive),
        "negative": " / ".join(negative),
    }


def _names_from_nodes(nodes: Any, input_keys: tuple[str, ...]) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    if not isinstance(nodes, list):
        return entries
    for node in nodes:
        if not isinstance(node, dict):
            continue
        inputs = node.get("inputs")
        if not isinstance(inputs, dict):
            continue
        for key in input_keys:
            value = inputs.get(key)
            if isinstance(value, str) and value.strip():
                entries.append(
                    {
                        "node_id": str(node.get("node_id", "")),
                        "file": value.strip(),
                    }
                )
    return entries


def extract_model_snapshot(report: dict[str, Any]) -> dict[str, Any]:
    """Freeze the recognized checkpoint / LoRA / VAE / CLIP file names.

    Only values the workflow parser already recognized are recorded; an
    unrecognized or missing model stays absent rather than being filled in.
    """
    model_nodes = report.get("model_nodes")
    lora_nodes = report.get("lora_nodes")
    return {
        "checkpoints": _names_from_nodes(
            model_nodes, ("ckpt_name", "unet_name")
        ),
        "loras": _names_from_nodes(lora_nodes, ("lora_name",)),
        "vaes": _names_from_nodes(model_nodes, ("vae_name",)),
        "clips": _names_from_nodes(
            model_nodes, ("clip_name", "clip_name1", "clip_name2")
        ),
    }


def extract_images(outputs: Any) -> list[dict[str, Any]]:
    """Index image file names from a ComfyUI history outputs payload.

    ``outputs`` maps node id to ``{"images": [{"filename", "subfolder",
    "type"}]}``. The on-disk existence check is a later slice; here only the
    recorded metadata is kept.
    """
    images: list[dict[str, Any]] = []
    if not isinstance(outputs, dict):
        return images
    for node_id, payload in outputs.items():
        candidates: list[Any] = []
        if isinstance(payload, list):
            candidates = payload
        elif isinstance(payload, dict):
            candidates = payload.get("images") or []
        for image in candidates:
            if not isinstance(image, dict):
                continue
            filename = image.get("filename")
            if not isinstance(filename, str) or not filename.strip():
                continue
            images.append(
                {
                    "node_id": str(node_id),
                    "filename": filename.strip(),
                    "subfolder": image.get("subfolder") or "",
                    "type": image.get("type") or "",
                    "exists": None,
                }
            )
    return images


def annotate_exists(
    images: list[dict[str, Any]], output_dir: str | None
) -> list[dict[str, Any]]:
    """Mark each recorded image with on-disk existence.

    Without a configured output directory the status stays ``None`` rather
    than being guessed. A resolved path that escapes the output directory is
    treated as missing; original images are never copied or touched here.
    """
    if not images:
        return images
    if not output_dir or not str(output_dir).strip():
        for image in images:
            image["exists"] = None
        return images

    base = Path(str(output_dir).strip()).expanduser()
    try:
        base_resolved = base.resolve()
    except OSError:
        base_resolved = base

    for image in images:
        filename = image.get("filename")
        if not isinstance(filename, str) or not filename:
            image["exists"] = False
            continue
        subfolder = image.get("subfolder") or ""
        candidate = (base_resolved / subfolder / filename).resolve()
        try:
            candidate.relative_to(base_resolved)
            image["exists"] = candidate.is_file()
        except (ValueError, OSError):
            image["exists"] = False
    return images


def record_snapshot(
    connection: sqlite3.Connection,
    prompt_id: str,
    workflow_id: str,
    working_prompts: list[dict[str, Any]],
    report: dict[str, Any],
    status: str,
) -> dict[str, Any]:
    prompts = extract_prompts(working_prompts)
    snapshot = extract_model_snapshot(report)
    now = _now()
    connection.execute(
        """
        INSERT OR IGNORE INTO generation_history
            (prompt_id, workflow_id, created_at, positive_prompt,
             negative_prompt, model_snapshot, task_status, images, last_error)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            prompt_id,
            workflow_id,
            now,
            prompts["positive"] or None,
            prompts["negative"] or None,
            json.dumps(snapshot, ensure_ascii=False),
            status,
            None,
            None,
        ),
    )
    connection.commit()
    return get_by_prompt_id(connection, prompt_id)


def update_task_status(
    connection: sqlite3.Connection,
    prompt_id: str,
    status: str,
    last_error: str | None = None,
) -> None:
    connection.execute(
        """
        UPDATE generation_history
        SET task_status = ?, last_error = ?
        WHERE prompt_id = ?
        """,
        (status, last_error, prompt_id),
    )
    connection.commit()


def attach_images(
    connection: sqlite3.Connection,
    prompt_id: str,
    images: list[dict[str, Any]],
) -> None:
    connection.execute(
        """
        UPDATE generation_history
        SET images = ?
        WHERE prompt_id = ?
        """,
        (json.dumps(images, ensure_ascii=False), prompt_id),
    )
    connection.commit()


def get_by_prompt_id(
    connection: sqlite3.Connection, prompt_id: str
) -> dict[str, Any] | None:
    row = connection.execute(
        "SELECT * FROM generation_history WHERE prompt_id = ?",
        (prompt_id,),
    ).fetchone()
    return _row(row)


def list_history(
    connection: sqlite3.Connection, workflow_id: str | None = None
) -> list[dict[str, Any]]:
    if workflow_id:
        rows = connection.execute(
            "SELECT * FROM generation_history WHERE workflow_id = ? "
            "ORDER BY created_at DESC",
            (workflow_id,),
        ).fetchall()
    else:
        rows = connection.execute(
            "SELECT * FROM generation_history ORDER BY created_at DESC"
        ).fetchall()
    return [record for record in (_row(row) for row in rows) if record]
