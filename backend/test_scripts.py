"""Unit tests for launcher / stopper safety logic (no real process spawned)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"


def _load(module_name: str, file_name: str):
    spec = importlib.util.spec_from_file_location(module_name, SCRIPTS_DIR / file_name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_launcher_loopback_accepts_local():
    launcher = _load("launcher", "workbench_launcher.py")
    for host in ("127.0.0.1", "localhost", "::1"):
        assert launcher.is_loopback_host(host) is True


def test_launcher_loopback_rejects_public_lan():
    launcher = _load("launcher", "workbench_launcher.py")
    for host in ("0.0.0.0", "192.168.1.20", "172.16.0.3", "203.0.113.7"):
        assert launcher.is_loopback_host(host) is False


def test_launcher_health_requires_identity(monkeypatch):
    launcher = _load("launcher", "workbench_launcher.py")

    class _Conn:
        def __init__(self, status, body):
            self._status = status
            self._body = body

        def request(self, method, path):
            pass

        def getresponse(self):
            return self

        def read(self):
            return self._body

        def close(self):
            pass

    # A server that returns an empty 200 (no app identity) must NOT count.
    monkeypatch.setattr(launcher.http.client, "HTTPConnection",
                        lambda host, port, timeout: _Conn(200, b"{}"))
    assert launcher.health_identifies_workbench("127.0.0.1", 8000) is False

    # The real workbench health body carries the app identifier.
    body = b'{"ok":true,"app":"ComfyUI-Prompt-Workbench","version":"0.1.0-dev.4"}'
    monkeypatch.setattr(launcher.http.client, "HTTPConnection",
                        lambda host, port, timeout: _Conn(200, body))
    assert launcher.health_identifies_workbench("127.0.0.1", 8000) is True


def test_stopper_rejects_identity_mismatch(monkeypatch):
    stopper = _load("stopper", "workbench_stopper.py")

    # PID reused by a process whose executable is not the project venv.
    monkeypatch.setattr(
        stopper, "_process_info",
        lambda pid: {
            "ExecutablePath": "C:/OtherApp/python.exe",
            "CommandLine": "python -m http.server",
            "CreationDate": "20260101000000.000000+000",
        },
    )
    matches, reason = stopper.identify_workbench(999999)
    assert matches is False
    assert "venv" in reason

    # A process without readable identity fails closed.
    monkeypatch.setattr(stopper, "_process_info", lambda pid: None)
    matches, reason = stopper.identify_workbench(999999)
    assert matches is False


def test_stopper_matches_workbench_process(monkeypatch):
    stopper = _load("stopper", "workbench_stopper.py")
    venv = str(stopper.VENV_PYTHON).lower().replace("/", "\\")

    monkeypatch.setattr(
        stopper, "_process_info",
        lambda pid: {
            "ExecutablePath": venv,
            "CommandLine": f'"{venv}" -m uvicorn main:app --host 127.0.0.1 --port 8000',
            "CreationDate": "20260101000000.000000+000",
        },
    )
    matches, _ = stopper.identify_workbench(12345)
    assert matches is True
