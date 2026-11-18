"""ComfyUI / Ollama HTTP client for task submission and pre-submit gates.

Only read-only probes and one guarded submit live here. There is no cloud
fallback: every unreachable, timed-out, or malformed response fails closed
with a conservative report instead of a fabricated result.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

APP_MARKER = "ComfyUI-Prompt-Workbench"


def _post_json(
    url: str,
    payload: dict[str, Any],
    timeout: float,
) -> tuple[int, dict[str, Any] | None, str | None]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST")
    request.add_header("Content-Type", "application/json")
    request.add_header("User-Agent", APP_MARKER)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            status = response.status
        data = json.loads(raw) if raw.strip() else {}
        return status, (data if isinstance(data, dict) else None), None
    except (
        urllib.error.URLError,
        TimeoutError,
        OSError,
        json.JSONDecodeError,
    ) as exc:
        return 0, None, str(exc)


def _get_json(
    url: str,
    timeout: float,
) -> tuple[dict[str, Any] | None, str | None]:
    request = urllib.request.Request(url)
    request.add_header("User-Agent", APP_MARKER)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
        data = json.loads(raw)
        return (data if isinstance(data, dict) else None), None
    except (
        urllib.error.URLError,
        TimeoutError,
        OSError,
        json.JSONDecodeError,
    ) as exc:
        return None, str(exc)


def _queue_ids(items: Any) -> list[str]:
    ids: list[str] = []
    if not isinstance(items, list):
        return ids
    for item in items:
        if isinstance(item, list) and item and isinstance(item[0], str):
            ids.append(item[0])
    return ids


def fetch_task_states(
    comfyui_url: str,
    timeout: float = 2.5,
) -> dict[str, Any]:
    """Project queue and history details for local task status reconciliation.

    Only identifiers and a conservative status summary are read; nothing is
    submitted, cancelled, or reordered. A missing queue response fails closed
    with ``online=False`` and empty projections.
    """
    queue_data, queue_error = _get_json(
        comfyui_url.rstrip("/") + "/queue", timeout
    )
    history_data, history_error = _get_json(
        comfyui_url.rstrip("/") + "/history", timeout
    )

    if queue_data is None:
        return {
            "online": False,
            "error": queue_error,
            "running": [],
            "pending": [],
            "history": {},
        }

    history: dict[str, Any] = {}
    if isinstance(history_data, dict):
        for prompt_id, entry in history_data.items():
            if not isinstance(prompt_id, str) or not isinstance(entry, dict):
                continue
            status = entry.get("status")
            status_str: str | None = None
            completed: Any = None
            if isinstance(status, dict):
                raw_str = status.get("status_str")
                status_str = raw_str if isinstance(raw_str, str) else None
                completed = status.get("completed")
            history[prompt_id] = {
                "status_str": status_str,
                "completed": completed,
                "outputs": entry.get("outputs"),
            }

    return {
        "online": True,
        "error": history_error if history_data is None else None,
        "running": _queue_ids(queue_data.get("queue_running")),
        "pending": _queue_ids(queue_data.get("queue_pending")),
        "history": history,
    }


def comfyui_online(comfyui_url: str, timeout: float = 2.5) -> bool:
    """True only if /system_stats answers with a JSON body."""
    data, _ = _get_json(comfyui_url.rstrip("/") + "/system_stats", timeout)
    return data is not None


def loaded_ollama_models(
    ollama_url: str,
    timeout: float = 2.5,
) -> dict[str, Any]:
    """Read-only list of models currently loaded in Ollama (``/api/ps``)."""
    data, error = _get_json(ollama_url.rstrip("/") + "/api/ps", timeout)
    if data is None:
        return {"online": False, "models": [], "error": error}
    entries = data.get("models")
    names: list[str] = []
    if isinstance(entries, list):
        for item in entries:
            if isinstance(item, dict) and isinstance(item.get("name"), str):
                names.append(item["name"])
    return {"online": True, "models": names, "error": None}


def cancel_pending(
    comfyui_url: str,
    prompt_id: str,
    timeout: float = 5.0,
) -> dict[str, Any]:
    """Remove a pending prompt from the ComfyUI queue (``/queue`` delete)."""
    _status, _data, error = _post_json(
        comfyui_url.rstrip("/") + "/queue",
        {"delete": [prompt_id]},
        timeout,
    )
    return {"ok": error is None, "error": error}


def interrupt_running(
    comfyui_url: str,
    prompt_id: str,
    timeout: float = 5.0,
) -> dict[str, Any]:
    """Interrupt the running prompt identified by ``prompt_id`` (``/interrupt``)."""
    _status, _data, error = _post_json(
        comfyui_url.rstrip("/") + "/interrupt",
        {"prompt_id": prompt_id},
        timeout,
    )
    return {"ok": error is None, "error": error}


def submit_prompt(
    comfyui_url: str,
    prompt_api: dict[str, Any],
    client_id: str,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """Submit an API-format prompt to ComfyUI ``/prompt``.

    A response carrying non-empty ``node_errors`` is treated as a rejected
    submission. No task is retried automatically here.
    """
    target = comfyui_url.rstrip("/") + "/prompt"
    _status, data, error = _post_json(
        target,
        {"prompt": prompt_api, "client_id": client_id},
        timeout,
    )
    if error is not None or data is None:
        return {
            "ok": False,
            "prompt_id": None,
            "node_errors": None,
            "error": error or "提交响应无效",
        }

    prompt_id = data.get("prompt_id")
    node_errors = data.get("node_errors")
    if not isinstance(prompt_id, str) or not prompt_id:
        return {
            "ok": False,
            "prompt_id": None,
            "node_errors": node_errors,
            "error": "响应缺少 prompt_id",
        }
    if isinstance(node_errors, dict) and node_errors:
        return {
            "ok": False,
            "prompt_id": prompt_id,
            "node_errors": node_errors,
            "error": "ComfyUI 报告节点错误",
        }
    return {"ok": True, "prompt_id": prompt_id, "node_errors": {}, "error": None}
