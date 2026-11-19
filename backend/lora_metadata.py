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


def _manual_path(manual_dir: Path, name: str) -> Path | None:
    """Resolve the manual sidecar under the managed knowledge dir.

    Rejects absolute names and ``..`` traversal. The weight stem (extension
    stripped) is matched against ``<stem>.json``; a full-name ``.json`` is
    accepted as a fallback.
    """
    if not name or name in (".", ".."):
        return None
    candidate_name = Path(name)
    if candidate_name.is_absolute() or ".." in candidate_name.parts:
        return None
    try:
        base_resolved = manual_dir.resolve()
        stem = candidate_name.stem
        stem_path = (base_resolved / f"{stem}.json").resolve()
        stem_path.relative_to(base_resolved)
        if stem_path.is_file():
            return stem_path
        full_path = (base_resolved / f"{name}.json").resolve()
        full_path.relative_to(base_resolved)
        if full_path.is_file():
            return full_path
    except (ValueError, OSError):
        return None
    return None


def _clean_combo(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    name = _as_text(value.get("name") or value.get("title"))
    words = _as_text_list(value.get("trigger_words") or value.get("words"))
    if not name and not words:
        return None
    return {"name": name, "trigger_words": words}


def load_manual(manual_dir: str, name: str) -> dict[str, Any]:
    """Read the workbench-managed manual LoRA note (read-only).

    Manual notes live under the managed ``knowledge/lora`` directory and are
    never written into the ComfyUI LoRA directory. A missing or unreadable
    note returns an empty record rather than raising.
    """
    record: dict[str, Any] = {
        "present": False,
        "unreadable": False,
        "trigger_words": [],
        "description": "",
        "base_model": "",
        "combos": [],
    }
    if not manual_dir or not str(manual_dir).strip():
        return record
    base = Path(str(manual_dir).strip()).expanduser()
    if not base.is_dir():
        return record
    json_path = _manual_path(base, name)
    if json_path is None or not json_path.is_file():
        return record
    record["present"] = True
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        record["unreadable"] = True
        return record
    if not isinstance(data, dict):
        record["unreadable"] = True
        return record

    record["trigger_words"] = _as_text_list(data.get("trigger_words"))
    record["description"] = _as_text(data.get("description"))
    record["base_model"] = _as_text(data.get("base_model"))
    combos: list[dict[str, Any]] = []
    raw_combos = data.get("combos")
    if isinstance(raw_combos, list):
        for item in raw_combos:
            combo = _clean_combo(item)
            if combo is not None:
                combos.append(combo)
    record["combos"] = combos
    return record


def merge_lora_meta(sidecar: dict[str, Any], manual: dict[str, Any]) -> dict[str, Any]:
    """Merge manual note over the auto-scanned sidecar metadata.

    Manual fields win when populated; missing manual fields fall back to the
    sidecar. Trigger words are de-duplicated with manual words first. The
    source and manual-presence flags are reported conservatively.
    """
    triggers: list[str] = []
    seen: set[str] = set()
    for word in list(manual.get("trigger_words", [])) + list(
        sidecar.get("trigger_words", [])
    ):
        if isinstance(word, str) and word.strip() and word not in seen:
            seen.add(word)
            triggers.append(word.strip())

    description = manual.get("description") or sidecar.get("description") or ""
    base_model = manual.get("base_model") or sidecar.get("base_model") or ""
    combos = manual.get("combos", [])

    has_manual = bool(manual.get("present"))
    if has_manual:
        source = "manual"
    elif triggers or description or base_model:
        source = "sidecar"
    else:
        source = "none"

    merged: dict[str, Any] = {
        "name": sidecar.get("name", ""),
        "status": sidecar.get("status", "missing"),
        "has_json": bool(sidecar.get("has_json")),
        "trigger_words": triggers,
        "description": description,
        "base_model": base_model,
        "source": source,
        "manual_present": has_manual,
        "manual_unreadable": bool(manual.get("unreadable")),
        "combos": combos,
    }

    filled = bool(triggers) + bool(description) + bool(base_model)
    if has_manual and not manual.get("unreadable"):
        # A readable manual note supplies the curated record; keep the
        # complete/partial split based on populated fields.
        merged["status"] = "complete" if filled >= 2 else "partial" if filled == 1 else "empty"
    elif filled >= 2:
        merged["status"] = "complete"
    elif filled == 1:
        merged["status"] = "partial"
    else:
        merged["status"] = sidecar.get("status", "empty")
    return merged


def scan_lora_metadata(
    lora_dir: str, names: list[str], manual_dir: str = ""
) -> dict[str, dict[str, Any]]:
    """Batch metadata lookup keyed by LoRA weight name (read-only).

    When ``manual_dir`` is given, managed manual notes are merged over the
    auto-scanned sidecar, manual fields winning.
    """
    result: dict[str, dict[str, Any]] = {}
    for name in names:
        if isinstance(name, str) and name:
            sidecar = describe_lora(lora_dir, name)
            if manual_dir:
                manual = load_manual(manual_dir, name)
                result[name] = merge_lora_meta(sidecar, manual)
            else:
                result[name] = sidecar
    return result
