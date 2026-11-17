from __future__ import annotations

import hmac
import json
import os
import platform
import secrets
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

APP_NAME = "ComfyUI-Prompt-Workbench"
SESSION_TOKEN = os.environ.get("WORKBENCH_SESSION_TOKEN", "")
DATA_ROOT = Path(
    os.environ.get(
        "WORKBENCH_DATA_ROOT",
        str(
            Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
            / APP_NAME
        ),
    )
).expanduser()

def default_settings() -> dict[str, Any]:
    root = DATA_ROOT
    return {
        "version": 1,
        "storage": {
            "root": str(root),
            "database": str(root / "database"),
            "knowledge": str(root / "knowledge"),
            "prompts": str(root / "prompts"),
            "workflows": str(root / "workflows"),
            "drafts": str(root / "drafts"),
            "history": str(root / "history"),
            "cache": str(root / "cache"),
            "logs": str(root / "logs"),
            "backups": str(root / "backups"),
            "exports": str(root / "exports"),
            "checkpoint": "",
            "lora": "",
        },
        "connections": {
            "ollama_url": "http://127.0.0.1:11434",
            "comfyui_url": "http://127.0.0.1:8188",
        },
    }

SETTINGS_FILE = DATA_ROOT / "settings.json"

def ensure_managed_directories(settings: dict[str, Any]) -> None:
    storage = settings.get("storage", {})
    for key, value in storage.items():
        if key in {"checkpoint", "lora"}:
            continue
        if isinstance(value, str) and value.strip():
            Path(value).expanduser().mkdir(parents=True, exist_ok=True)

def load_settings() -> dict[str, Any]:
    DATA_ROOT.mkdir(parents=True, exist_ok=True)

    if SETTINGS_FILE.exists():
        try:
            loaded = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            defaults = default_settings()
            defaults["storage"].update(loaded.get("storage", {}))
            defaults["connections"].update(loaded.get("connections", {}))
            loaded = defaults
        except (OSError, json.JSONDecodeError, TypeError):
            loaded = default_settings()
    else:
        loaded = default_settings()

    ensure_managed_directories(loaded)
    save_settings_file(loaded)
    return loaded

def save_settings_file(settings: dict[str, Any]) -> None:
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    temp_file = SETTINGS_FILE.with_suffix(".json.tmp")
    temp_file.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp_file.replace(SETTINGS_FILE)

class SettingsUpdate(BaseModel):
    storage: dict[str, str] = Field(default_factory=dict)
    connections: dict[str, str] = Field(default_factory=dict)

class StorageValidation(BaseModel):
    path: str
    create: bool = False

app = FastAPI(
    title=APP_NAME,
    version="0.1.0-dev.1",
    docs_url=None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "tauri://localhost",
        "https://tauri.localhost",
        "http://tauri.localhost",
        "http://localhost:1420",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

@app.middleware("http")
async def require_session_token(request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)

    supplied = request.headers.get("Authorization", "")
    expected = f"Bearer {SESSION_TOKEN}"

    if not SESSION_TOKEN or not hmac.compare_digest(supplied, expected):
        from starlette.responses import JSONResponse

        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid or missing local session token"},
        )

    return await call_next(request)

@app.get("/api/health")
def health():
    return {
        "ok": True,
        "app": APP_NAME,
        "version": app.version,
        "python": platform.python_version(),
        "platform": platform.platform(),
    }

@app.get("/api/settings")
def get_settings():
    return load_settings()

@app.post("/api/settings")
def update_settings(payload: SettingsUpdate):
    current = load_settings()

    allowed_storage = set(current["storage"].keys())
    for key, value in payload.storage.items():
        if key not in allowed_storage:
            raise HTTPException(400, f"Unknown storage key: {key}")
        if key in {"checkpoint", "lora"}:
            # External model folders are optional and are not moved.
            current["storage"][key] = value.strip()
            continue
        if not value.strip():
            raise HTTPException(400, f"Storage path cannot be empty: {key}")
        current["storage"][key] = str(Path(value).expanduser())

    allowed_connections = {"ollama_url", "comfyui_url"}
    for key, value in payload.connections.items():
        if key not in allowed_connections:
            raise HTTPException(400, f"Unknown connection key: {key}")
        if not value.startswith(("http://", "https://")):
            raise HTTPException(400, f"Invalid URL: {key}")
        current["connections"][key] = value.rstrip("/")

    try:
        ensure_managed_directories(current)
        save_settings_file(current)
    except OSError as exc:
        raise HTTPException(400, f"Cannot create or save configured paths: {exc}") from exc

    return current

@app.post("/api/storage/validate")
def validate_storage(payload: StorageValidation):
    raw = payload.path.strip()
    if not raw:
        raise HTTPException(400, "Path is empty")

    path = Path(raw).expanduser()

    try:
        if payload.create:
            path.mkdir(parents=True, exist_ok=True)

        exists = path.exists()
        is_dir = path.is_dir()
        writable = False

        if exists and is_dir:
            probe = path / f".workbench-write-test-{secrets.token_hex(6)}"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            writable = True

        return {
            "path": str(path),
            "exists": exists,
            "is_directory": is_dir,
            "writable": writable,
        }
    except OSError as exc:
        raise HTTPException(400, f"Path validation failed: {exc}") from exc

def probe_url(url: str, path: str) -> dict[str, Any]:
    target = url.rstrip("/") + path
    request = Request(target, headers={"User-Agent": APP_NAME})

    try:
        with urlopen(request, timeout=2.5) as response:
            return {
                "online": 200 <= response.status < 300,
                "status_code": response.status,
                "url": url,
                "error": None,
            }
    except (URLError, TimeoutError, OSError) as exc:
        return {
            "online": False,
            "status_code": None,
            "url": url,
            "error": str(exc),
        }

@app.get("/api/services/status")
def services_status():
    settings = load_settings()
    connections = settings["connections"]

    ollama = probe_url(connections["ollama_url"], "/api/tags")
    comfyui = probe_url(connections["comfyui_url"], "/system_stats")

    return {
        "ollama": ollama,
        "comfyui": comfyui,
    }
