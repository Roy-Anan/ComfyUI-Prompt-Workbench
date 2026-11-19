"""Read-only LoRA sidecar metadata inspection (R98 skeleton).

This module reads a ``<lora>.json`` sidecar next to a LoRA weight file and
extracts trigger words, a description and the base model when present. It is
strictly read-only: weights are never copied or modified, and no character card
is written into the ComfyUI directory.

Supported status values:
  * ``complete``  - sidecar readable and at least two of trigger words /
                    description / base model are populated.
  * ``partial``   - sidecar readable but only one field is populated.
  * ``empty``     - sidecar readable but carries no recognized fields.
  * ``missing``   - no sidecar file next to the weight.
  * ``unreadable``- sidecar exists but fails to parse as JSON.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

TRIGGER_KEYS = (
    "trigger_words",
    "triggerWords",
    "trained_words",
    "trainedWords",
    "tags",
    "keywords",
)
DESC_KEYS = ("description", "notes", "summary", "blurb")
BASE_KEYS = ("base_model", "baseModel", "model")


def _as_text_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                out.append(item.strip())
            elif isinstance(item, dict):
                for key in ("name", "keyword", "trigger", "value"):
                    candidate = item.get(key)
                    if isinstance(candidate, str) and candidate.strip():
                        out.append(candidate.strip())
                        break
        return out
    if isinstance(value, str):
        return [
            part.strip()
            for part in value.replace("\n", ",").split(",")
            if part.strip()
        ]
    return []


def _as_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("name", "title", "value"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
    return ""


def _sidecar_path(base: Path, name: str) -> Path | None:
    """Resolve the sidecar JSON path, rejecting traversal and absolute names."""
    if not name or name in (".", ".."):
        return None
    candidate_name = Path(name)
    if candidate_name.is_absolute() or ".." in candidate_name.parts:
        return None
    try:
        base_resolved = base.resolve()
        resolved = (base_resolved / name).resolve()
        resolved.relative_to(base_resolved)
    except (ValueError, OSError):
        return None
    return resolved.with_suffix(".json")


def describe_lora(lora_dir: str, name: str) -> dict[str, Any]:
    """Return a read-only metadata summary for one LoRA weight name."""
    meta: dict[str, Any] = {
        "name": name,
        "status": "missing",
        "has_json": False,
        "trigger_words": [],
        "description": "",
        "base_model": "",
    }
    if not lora_dir or not str(lora_dir).strip():
        return meta

    base = Path(str(lora_dir).strip()).expanduser()
    if not base.is_dir():
        return meta

    json_path = _sidecar_path(base, name)
    if json_path is None or not json_path.is_file():
        return meta
    meta["has_json"] = True

    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        meta["status"] = "unreadable"
        return meta

    if not isinstance(data, dict):
        meta["status"] = "empty"
        return meta

    triggers: list[str] = []
    for key in TRIGGER_KEYS:
        triggers.extend(_as_text_list(data.get(key)))
    seen: set[str] = set()
    triggers = [word for word in triggers if not (word in seen or seen.add(word))]

    description = next(
        (_as_text(data.get(key)) for key in DESC_KEYS if _as_text(data.get(key))),
        "",
    )
    base_model = next(
        (_as_text(data.get(key)) for key in BASE_KEYS if _as_text(data.get(key))),
        "",
    )

    meta.update(
        {
            "trigger_words": triggers,
            "description": description,
            "base_model": base_model,
        }
    )

    filled = bool(triggers) + bool(description) + bool(base_model)
    if filled >= 2:
        meta["status"] = "complete"
    elif filled == 1:
        meta["status"] = "partial"
    else:
        meta["status"] = "empty"
    return meta


def scan_lora_metadata(
    lora_dir: str, names: list[str]
) -> dict[str, dict[str, Any]]:
    """Batch metadata lookup keyed by LoRA weight name (read-only)."""
    result: dict[str, dict[str, Any]] = {}
    for name in names:
        if isinstance(name, str) and name:
            result[name] = describe_lora(lora_dir, name)
    return result
