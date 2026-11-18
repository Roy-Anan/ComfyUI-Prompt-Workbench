"""Workbench local Web runtime launcher (Windows).

Started by the double-click batch entry. It:
  * reuses the project virtualenv interpreter (never the ComfyUI bundled Python)
  * enforces a loopback bind (refuses 0.0.0.0, LAN and public addresses)
  * checks whether the configured port already serves this workbench (identity check)
  * starts FastAPI as a detached tracked process and records its PID to a file
  * waits for the health endpoint to identify the real workbench, then opens
    the default browser

The backend process survives after this launcher returns. The PID file is kept
so the stopper can terminate exactly this workbench process tree.
"""

from __future__ import annotations

import http.client
import ipaddress
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VENV_PYTHON = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
BACKEND_DIR = REPO_ROOT / "backend"
PID_FILE = REPO_ROOT / ".workbench.pid"
# Structured runtime record; the plain PID file is kept as a fallback, but the
# stopper verifies identity against this record rather than the PID alone.
RUNTIME_RECORD_FILE = REPO_ROOT / ".workbench-runtime.json"
HOST = os.environ.get("WORKBENCH_HOST", "127.0.0.1")
PORT = int(os.environ.get("WORKBENCH_PORT", "17890"))
HEALTH_PATH = "/api/health"
APP_ID = "ComfyUI-Prompt-Workbench"
OPEN_BROWSER = os.environ.get("WORKBENCH_OPEN_BROWSER", "1") != "0"


def is_loopback_host(host: str) -> bool:
    """Only explicit loopback names/addresses are allowed to bind."""
    host = host.strip().lower()
    if host in {"localhost", "127.0.0.1", "::1"}:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
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


def port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1.0)
        return sock.connect_ex((host, port)) == 0


def health_identifies_workbench(host: str, port: int, timeout: float = 1.0) -> bool:
    """True only if /api/health responds with this app's identity.

    A bare HTTP response (even a 401) proves something is listening, but not
    that it is the workbench. We require the health body to carry the expected
    app identifier; an unauthenticated 401 on /api/health still returns the
    app identity field, so this check works before a session ticket exists.
    """
    try:
        conn = http.client.HTTPConnection(host, port, timeout=timeout)
        conn.request("GET", HEALTH_PATH)
        response = conn.getresponse()
        body = response.read()
        conn.close()
    except (OSError, http.client.HTTPException):
        return False

    try:
        payload = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return False

    return payload.get("app") == APP_ID or payload.get("app_id") == APP_ID


def read_pid() -> int | None:
    if not PID_FILE.exists():
        return None
    try:
        return int(PID_FILE.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def _powershell_exe() -> str:
    """Resolve a usable PowerShell launcher (pwsh 7, powershell, legacy 5.1 path)."""
    found = shutil.which("pwsh") or shutil.which("powershell")
    if found:
        return found
    return os.path.join(
        os.environ.get("WINDIR", r"C:\Windows"),
        "System32",
        "WindowsPowerShell",
        "v1.0",
        "powershell.exe",
    )


def _process_creation_date(pid: int) -> str | None:
    """Read the Win32 CreationDate as an ISO8601 instant, comparable on both sides.

    Right after Popen the new process may not yet report its CreationDate, so
    retry briefly before giving up; a persistent None is tolerated by the
    stopper (identity still rests on the per-launch instance id).
    """
    ps = (
        "Get-CimInstance Win32_Process -Filter "
        f'"ProcessId={pid}" | '
        "ForEach-Object { $_.CreationDate.ToString(\"yyyy-MM-ddTHH:mm:ss.ffffffZ\") }"
    )
    for _ in range(5):
        try:
            output = subprocess.check_output(
                [_powershell_exe(), "-NoProfile", "-Command", ps],
                text=True,
                stderr=subprocess.DEVNULL,
            )
        except (OSError, subprocess.CalledProcessError):
            return None
        value = output.strip()
        if value:
            return value
        time.sleep(0.2)
    return None


def write_runtime_record(proc: subprocess.Popen, instance_id: str) -> None:
    """Persist a structured identity record for the tracked backend process."""
    record = {
        "app_id": APP_ID,
        "instance_id": instance_id,
        "pid": proc.pid,
        "creation_date": _process_creation_date(proc.pid),
        "executable_path": str(VENV_PYTHON),
        "working_directory": str(BACKEND_DIR),
        "command_line": [
            str(VENV_PYTHON),
            "-m",
            "uvicorn",
            "main:app",
            "--host",
            HOST,
            "--port",
            str(PORT),
        ],
        "host": HOST,
        "port": PORT,
    }
    PID_FILE.write_text(str(proc.pid), encoding="utf-8")
    RUNTIME_RECORD_FILE.write_text(
        json.dumps(record, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def read_runtime_record() -> dict | None:
    """Read the structured record; None when missing or corrupt."""
    if not RUNTIME_RECORD_FILE.exists():
        return None
    try:
        data = json.loads(RUNTIME_RECORD_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def clear_runtime_record() -> None:
    PID_FILE.unlink(missing_ok=True)
    RUNTIME_RECORD_FILE.unlink(missing_ok=True)


def pid_alive(pid: int) -> bool:
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, pid)
        if not handle:
            return False
        exit_code = ctypes.c_ulong()
        alive = kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
        kernel32.CloseHandle(handle)
        return bool(alive) and exit_code.value == 259
    except OSError:
        return False


def main() -> int:
    if not is_loopback_host(HOST):
        print(
            f"[工作台] 拒绝绑定非本机地址 '{HOST}'：工作台只允许监听 127.0.0.1，"
            "不开放局域网或公网。"
        )
        return 1

    if not VENV_PYTHON.is_file():
        print("[工作台] 未找到项目独立 Python 环境：", VENV_PYTHON)
        print("[工作台] 请先在项目 .venv 中准备依赖，不要使用 ComfyUI 整合包的 Python。")
        return 1

    existing_pid = read_pid()
    if existing_pid and pid_alive(existing_pid) and port_in_use(HOST, PORT):
        if health_identifies_workbench(HOST, PORT):
            print(f"[工作台] 已有实例在运行（PID {existing_pid}，端口 {PORT}）。")
            if OPEN_BROWSER:
                import webbrowser

                webbrowser.open(f"http://{HOST}:{PORT}")
            return 0
        print(
            f"[工作台] 端口 {PORT} 被其他程序占用，且不是本工作台实例；"
            "不会结束该进程，请先关闭占用程序。"
        )
        return 1

    if port_in_use(HOST, PORT):
        if health_identifies_workbench(HOST, PORT):
            print(f"[工作台] 端口 {PORT} 已由本工作台实例占用，直接复用。")
            if OPEN_BROWSER:
                import webbrowser

                webbrowser.open(f"http://{HOST}:{PORT}")
            return 0
        print(f"[工作台] 端口 {PORT} 已被其他程序占用，无法启动工作台。")
        print("[工作台] 请关闭占用该端口的程序后重试；本脚本不会自动结束其他进程。")
        return 1

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    # Bootstrap token is generated per launch and kept in this process only;
    # it is never written into the frontend build or committed.
    if not env.get("WORKBENCH_SESSION_TOKEN"):
        env["WORKBENCH_SESSION_TOKEN"] = secrets.token_urlsafe(32)

    # Per-launch random instance identity, recorded so the stopper can tell
    # this backend apart from a PID reused by another program.
    instance_id = secrets.token_urlsafe(16)
    env["WORKBENCH_INSTANCE_ID"] = instance_id

    print(f"[工作台] 正在启动本地服务：http://{HOST}:{PORT}")

    # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP so the backend keeps running
    # after this launcher returns; the structured record tracks the root.
    creation_flags = 0x00000008 | 0x00000200
    cmd = [
        str(VENV_PYTHON),
        "-m",
        "uvicorn",
        "main:app",
        "--host",
        HOST,
        "--port",
        str(PORT),
    ]
    proc = subprocess.Popen(
        cmd,
        cwd=str(BACKEND_DIR),
        env=env,
        creationflags=creation_flags,
        close_fds=True,
    )

    write_runtime_record(proc, instance_id)

    ready = False
    for _ in range(30):
        if proc.poll() is not None:
            print("[工作台] 服务进程已退出，启动失败。请查看上方错误信息。")
            clear_runtime_record()
            return 1
        if health_identifies_workbench(HOST, PORT):
            ready = True
            break
        time.sleep(0.5)

    if not ready:
        print("[工作台] 健康检查超时：未识别到本工作台实例，服务未在预期时间内就绪。")
        return 1

    print(f"[工作台] 服务已就绪（PID {proc.pid}）。")
    if OPEN_BROWSER:
        import webbrowser

        webbrowser.open(f"http://{HOST}:{PORT}")
        print("[工作台] 已在默认浏览器打开工作台。")

    print("[工作台] 服务在后台运行；运行停止脚本或关闭相关进程即可停止。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
