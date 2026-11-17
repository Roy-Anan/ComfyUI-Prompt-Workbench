from __future__ import annotations

import hmac
import json
import os
import platform
import secrets
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request as UrlRequest, urlopen

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

import datadir

APP_NAME = "ComfyUI-Prompt-Workbench"
APP_VERSION = "0.1.0-dev.4"

# Bootstrapping token: only used to request a per-session ticket. In the
# local Web runtime it is generated per launch by the start script and passed
# through an environment variable; it is never baked into the frontend build.
BOOTSTRAP_TOKEN = os.environ.get("WORKBENCH_SESSION_TOKEN", "")

# Unified data root: <repo>/userdata by default; overridable via env var.
DATA_ROOT = datadir.default_data_root()
SETTINGS_FILE = datadir.settings_path(DATA_ROOT)

# Frontend build directory served by FastAPI in the local Web runtime.
BACKEND_DIR = Path(__file__).resolve().parent
FRONTEND_DIST = BACKEND_DIR.parent / "frontend" / "dist"

MANAGED_KEYS = set(datadir.MANAGED_KEYS)
OPTIONAL_EXTERNAL_KEYS = set(datadir.OPTIONAL_EXTERNAL_KEYS)
ALLOWED_STORAGE_KEYS = MANAGED_KEYS | OPTIONAL_EXTERNAL_KEYS | {"root"}
ALLOWED_CONNECTION_KEYS = {"ollama_url", "comfyui_url"}

# Migration report for the current process; populated on first settings load.
MIGRATION_REPORT: dict[str, Any] = {}

# Local-only origins allowed by CORS. The production Web runtime is same-origin
# (FastAPI serves both API and frontend), so no broad LAN/public origin is added.
ALLOWED_ORIGINS = {
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://127.0.0.1:1420",
    "http://localhost:1420",
}

# Per-session tickets handed to the browser via an HttpOnly cookie. They are
# generated at bootstrap and held only in process memory.
SESSION_TICKETS: set[str] = set()

CSRF_HEADER = "X-Workbench-CSRF"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


def default_settings() -> dict[str, Any]:
    return datadir.default_settings(DATA_ROOT)


def write_test(path: Path) -> None:
    probe = path / f".workbench-write-test-{secrets.token_hex(8)}"
    try:
        probe.write_text("ok", encoding="utf-8")
    finally:
        try:
            probe.unlink(missing_ok=True)
        except OSError:
            pass


def ensure_managed_directories(settings: dict[str, Any]) -> None:
    for key in MANAGED_KEYS:
        raw = settings["storage"].get(key)
        if not isinstance(raw, str) or not raw.strip():
            raise ValueError(f"Managed storage path is empty: {key}")

        path = Path(raw).expanduser()
        path.mkdir(parents=True, exist_ok=True)

        if not path.is_dir():
            raise ValueError(f"Storage path is not a directory: {key}")

        write_test(path)


def initialize_database(settings: dict[str, Any]) -> str:
    database_dir = Path(settings["storage"]["database"]).expanduser()
    database_dir.mkdir(parents=True, exist_ok=True)

    if not database_dir.is_dir():
        raise ValueError("Database path is not a directory")

    database_path = database_dir / "workbench.sqlite3"

    with sqlite3.connect(database_path, timeout=10) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        connection.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS app_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        row = connection.execute(
            "SELECT MAX(version) FROM schema_version"
        ).fetchone()

        if row is None or row[0] is None:
            connection.execute(
                """
                INSERT INTO schema_version(version, applied_at)
                VALUES (?, ?)
                """,
                (1, datetime.now(timezone.utc).isoformat()),
            )

        connection.execute(
            """
            INSERT INTO app_metadata(key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            (
                "application",
                APP_NAME,
                datetime.now(timezone.utc).isoformat(),
            ),
        )

    return str(database_path)


def save_settings_file(settings: dict[str, Any]) -> None:
    datadir.save_settings_file(DATA_ROOT, settings)


def backup_corrupt_settings() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    backup = SETTINGS_FILE.with_name(
        f"settings.corrupt-{timestamp}-{secrets.token_hex(3)}.json"
    )
    shutil.copy2(SETTINGS_FILE, backup)
    return backup


def load_settings() -> dict[str, Any]:
    global MIGRATION_REPORT

    # Prepare managed directories and migrate any legacy data once per process.
    MIGRATION_REPORT = datadir.prepare_root(DATA_ROOT)
    settings = default_settings()

    try:
        loaded = datadir.load_settings_file(DATA_ROOT)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        loaded = None
        try:
            backup_corrupt_settings()
        except OSError as exc:
            raise RuntimeError(
                f"Settings are corrupt and backup failed: {exc}"
            ) from exc

    if loaded is not None:
        storage = loaded.get("storage", {})
        connections = loaded.get("connections", {})

        if not isinstance(storage, dict):
            raise ValueError("Settings storage must be an object")
        if not isinstance(connections, dict):
            raise ValueError("Settings connections must be an object")

        # Preserve only external ComfyUI paths; managed paths are rebuilt
        # against the current data root so a legacy AppData path is not kept.
        for key in OPTIONAL_EXTERNAL_KEYS:
            if key in storage and isinstance(storage[key], str):
                settings["storage"][key] = storage[key]

        for key in ALLOWED_CONNECTION_KEYS:
            if key in connections and isinstance(connections[key], str):
                settings["connections"][key] = connections[key]

    ensure_managed_directories(settings)
    initialize_database(settings)
    save_settings_file(settings)
    return settings


class SettingsUpdate(BaseModel):
    storage: dict[str, str] = Field(default_factory=dict)
    connections: dict[str, str] = Field(default_factory=dict)


class StorageValidation(BaseModel):
    path: str
    create: bool = False


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    docs_url=None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(ALLOWED_ORIGINS),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", CSRF_HEADER],
)


def _origin_allowed(request: Request) -> bool:
    origin = request.headers.get("Origin")
    if not origin:
        # Same-origin browser navigations and same-origin fetch often omit
        # Origin; loopback non-browser clients are covered by the token check.
        return True
    return origin in ALLOWED_ORIGINS


def _authorized(request: Request) -> tuple[bool, str]:
    """Return (authorized, session_kind).

    session_kind is "cookie" for the browser ticket, "bearer" for the
    bootstrap token (start script / tests / local CLI), or "" when rejected.
    """
    # 1) Per-session ticket carried in an HttpOnly cookie (browser runtime).
    cookie_ticket = request.cookies.get("workbench_session")
    if cookie_ticket and cookie_ticket in SESSION_TICKETS:
        return True, "cookie"

    # 2) Bootstrap token via Bearer header (start script / tests / local CLI).
    supplied = request.headers.get("Authorization", "")
    expected = f"Bearer {BOOTSTRAP_TOKEN}"
    if BOOTSTRAP_TOKEN and hmac.compare_digest(supplied, expected):
        return True, "bearer"

    return False, ""


@app.middleware("http")
async def require_session(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)

    # Static frontend assets and the SPA shell are served without API auth.
    if not request.url.path.startswith("/api"):
        return await call_next(request)

    # The health endpoint is an unauthenticated identity probe: the launcher
    # uses it to confirm the listener is actually this workbench before
    # issuing a session. It exposes only app id/version, no user data.
    if request.url.path == "/api/health":
        return await call_next(request)

    # Reject cross-origin state changes from untrusted origins.
    if request.method not in SAFE_METHODS and not _origin_allowed(request):
        return JSONResponse(
            status_code=403,
            content={"detail": "Origin not allowed"},
        )

    # /api/bootstrap performs its own origin/token check and issues the ticket.
    if request.url.path != "/api/bootstrap":
        authorized, session_kind = _authorized(request)
        if not authorized:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing local session"},
            )
    else:
        authorized, session_kind = _authorized(request)

    # CSRF protection for browser cookie sessions on state-changing requests.
    # The Bearer bootstrap token is a non-browser caller and does not carry
    # ambient cookies, so it is exempt from the CSRF header check.
    if request.method not in SAFE_METHODS and session_kind == "cookie":
        csrf_cookie = request.cookies.get("workbench_csrf")
        csrf_header = request.headers.get(CSRF_HEADER, "")
        if not csrf_cookie or not hmac.compare_digest(csrf_cookie, csrf_header):
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token mismatch"},
            )

    return await call_next(request)


@app.get("/api/bootstrap")
def bootstrap(request: Request):
    """Issue a per-session ticket to the local browser.

    Same-origin loopback navigations/fetch omit Origin or send a loopback
    Origin and are issued a ticket directly. Any other origin must present the
    Bearer bootstrap token (script / CLI / tests). The ticket is stored in an
    HttpOnly cookie; a separate readable CSRF cookie protects state changes.
    """
    origin = request.headers.get("Origin")
    same_origin = not origin or origin in ALLOWED_ORIGINS

    if not same_origin:
        authorized, _ = _authorized(request)
        if not authorized:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing local session"},
            )

    ticket = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(32)
    SESSION_TICKETS.add(ticket)

    response = JSONResponse(
        {
            "ok": True,
            "app": APP_NAME,
            "version": APP_VERSION,
            "csrf": csrf,
        }
    )
    response.set_cookie(
        "workbench_session",
        ticket,
        httponly=True,
        samesite="Strict",
        secure=False,
        path="/",
        max_age=60 * 60 * 8,
    )
    response.set_cookie(
        "workbench_csrf",
        csrf,
        httponly=False,
        samesite="Strict",
        secure=False,
        path="/",
        max_age=60 * 60 * 8,
    )
    return response


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "app": APP_NAME,
        "app_id": APP_NAME,
        "version": APP_VERSION,
        "python": platform.python_version(),
        "platform": platform.platform(),
    }


@app.get("/api/settings")
def get_settings():
    try:
        return load_settings()
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Settings initialization failed: {exc}",
        ) from exc


@app.post("/api/settings")
def update_settings(payload: SettingsUpdate):
    current = load_settings()

    unknown_storage = set(payload.storage) - ALLOWED_STORAGE_KEYS
    if unknown_storage:
        raise HTTPException(
            400, f"Unknown storage keys: {sorted(unknown_storage)}"
        )

    if "root" in payload.storage:
        raise HTTPException(
            400,
            "storage.root is fixed by the local host and cannot be changed",
        )

    unknown_connections = set(payload.connections) - ALLOWED_CONNECTION_KEYS
    if unknown_connections:
        raise HTTPException(
            400,
            f"Unknown connection keys: {sorted(unknown_connections)}",
        )

    candidate = json.loads(json.dumps(current))

    for key, value in payload.storage.items():
        value = value.strip()

        if key in OPTIONAL_EXTERNAL_KEYS:
            if value:
                external_path = Path(value).expanduser()
                if not external_path.exists() or not external_path.is_dir():
                    raise HTTPException(
                        400,
                        f"External model directory does not exist: {key}",
                    )
            candidate["storage"][key] = value
            continue

        if not value:
            raise HTTPException(400, f"Storage path cannot be empty: {key}")

        candidate["storage"][key] = str(Path(value).expanduser())

    for key, value in payload.connections.items():
        value = value.strip()

        if not value.startswith(("http://", "https://")):
            raise HTTPException(400, f"Invalid URL: {key}")

        candidate["connections"][key] = value.rstrip("/")

    try:
        ensure_managed_directories(candidate)
        initialize_database(candidate)
        save_settings_file(candidate)
    except (OSError, ValueError, sqlite3.Error) as exc:
        raise HTTPException(
            400,
            f"Cannot validate or save settings: {exc}",
        ) from exc

    return candidate


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
            write_test(path)
            writable = True

        return {
            "path": str(path),
            "exists": exists,
            "is_directory": is_dir,
            "writable": writable,
        }

    except OSError as exc:
        raise HTTPException(
            400,
            f"Path validation failed: {exc}",
        ) from exc


def probe_url(url: str, path: str) -> dict[str, Any]:
    target = url.rstrip("/") + path
    request = UrlRequest(target)
    request.add_header("User-Agent", APP_NAME)

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

    return {
        "ollama": probe_url(
            connections["ollama_url"],
            "/api/tags",
        ),
        "comfyui": probe_url(
            connections["comfyui_url"],
            "/system_stats",
        ),
    }


# ---- Static frontend hosting (local Web runtime) ---------------------------

def _dist_ready() -> bool:
    return FRONTEND_DIST.is_dir() and (FRONTEND_DIST / "index.html").is_file()


def _resolve_within_dist(full_path: str) -> Path | None:
    """Resolve ``full_path`` against dist and confirm it stays inside dist.

    Uses real-path containment (not a string prefix) so ``../`` traversal and
    adjacent-directory prefix collisions (e.g. ``dist-other``) are rejected.
    URL-encoded traversal (``%2e%2e%2f``) is decoded before resolving.
    Returns None when the resolved path escapes dist.
    """
    from urllib.parse import unquote

    dist_root = FRONTEND_DIST.resolve()
    decoded = unquote(full_path)
    # Normalize away any traversal segments before joining.
    normalized = Path("/", decoded).as_posix().lstrip("/")
    candidate = (dist_root / normalized).resolve()

    try:
        candidate.relative_to(dist_root)
    except ValueError:
        return None
    return candidate


@app.get("/{full_path:path}")
def serve_frontend(request: Request, full_path: str):
    # Unknown /api routes must return JSON, never the SPA HTML.
    if full_path.startswith("api/") or full_path == "api":
        raise HTTPException(status_code=404, detail="API endpoint not found")

    if not _dist_ready():
        raise HTTPException(
            status_code=503,
            detail="Frontend build missing: run the frontend build before starting the Web runtime.",
        )

    requested = _resolve_within_dist(full_path)
    if requested is None:
        raise HTTPException(status_code=403, detail="Forbidden path")

    if requested.is_file():
        return FileResponse(requested)

    # SPA fallback: any non-API, non-asset route returns the app shell.
    return FileResponse(FRONTEND_DIST / "index.html")


def is_loopback_host(host: str) -> bool:
    """Return True only for explicit loopback addresses/names."""
    import ipaddress
    import socket

    host = host.strip().lower()
    if host in {"localhost", "127.0.0.1", "::1"}:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        # Resolve names defensively; only accept if every resolved address
        # is loopback.
        try:
            infos = socket.getaddrinfo(host, None)
        except OSError:
            return False
        for family, _, _, _, sockaddr in infos:
            try:
                addr = ipaddress.ip_address(sockaddr[0])
            except ValueError:
                return False
            if not addr.is_loopback:
                return False
        return bool(infos)


def main() -> None:
    import uvicorn

    host = os.environ.get("WORKBENCH_HOST", "127.0.0.1")
    port = int(os.environ.get("WORKBENCH_PORT", "8000"))

    # Default must stay loopback; refuse LAN/public binds.
    if not is_loopback_host(host):
        raise SystemExit(
            f"Refusing to bind to non-loopback host '{host}'. "
            "The local Web runtime defaults to 127.0.0.1."
        )

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        log_level="info",
        access_log=False,
    )


if __name__ == "__main__":
    main()
