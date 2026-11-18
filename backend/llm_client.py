"""Local Ollama chat client for prompt candidates (M4).

This module only talks to the configured local Ollama instance. There is
**no cloud fallback**: an unreachable host, timeout, non-JSON response or
empty message is reported as a conservative error with no fabricated
candidate text. The candidate returned here is never written back to a
workflow by this layer.
"""

from __future__ import annotations

import json
from typing import Any
from urllib.error import URLError
from urllib.request import Request as UrlRequest, urlopen

APP_NAME = "ComfyUI-Prompt-Workbench"
DEFAULT_TIMEOUT = 30.0


def chat(
    ollama_url: str,
    model: str,
    messages: list[dict[str, str]],
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Send one non-streaming chat round to local Ollama ``/api/chat``.

    Returns ``{"ok": True, "content": str, "model": str, "error": None}`` on
    a usable response, otherwise ``{"ok": False, "content": None, ...}`` with
    an error string. Callers must treat ``ok is False`` as a failed request
    and must not guess a candidate.
    """
    target = ollama_url.rstrip("/") + "/api/chat"
    payload = {"model": model, "messages": messages, "stream": False}
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = UrlRequest(target, data=body, method="POST")
    request.add_header("Content-Type", "application/json")
    request.add_header("User-Agent", APP_NAME)

    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
        data = json.loads(raw)
        message = data.get("message") if isinstance(data, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            return {
                "ok": False,
                "content": None,
                "model": model,
                "error": "empty model response",
            }
        return {
            "ok": True,
            "content": content.strip(),
            "model": model,
            "error": None,
        }
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "content": None,
            "model": model,
            "error": str(exc),
        }
