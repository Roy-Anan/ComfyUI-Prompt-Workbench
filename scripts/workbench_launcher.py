"""Workbench local Web runtime launcher (Windows).

Started by the double-click batch entry. It:
  * reuses the project virtualenv interpreter (never the ComfyUI bundled Python)
  * checks whether port 8000 is already in use by this workbench
  * starts FastAPI as a detached tracked process and records its PID to a file
  * waits for the health endpoint to respond, then opens the default browser

The backend process survives after this launcher returns. The PID file is kept
so the stopper can terminate exactly this workbench process tree.
"""

from __future__ import annotations

import http.client
import os
import secrets
import socket
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VENV_PYTHON = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
BACKEND_DIR = REPO_ROOT / "backend"
PID_FILE = REPO_ROOT / ".workbench.pid"
HOST = os.environ.get("WORKBENCH_HOST", "127.0.0.1")
PORT = int(os.environ.get("WORKBENCH_PORT", "8000"))
HEALTH_PATH = "/api/health"
OPEN_BROWSER = os.environ.get("WORKBENCH_OPEN_BROWSER", "1") != "0"


def port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1.0)
        return sock.connect_ex((host, port)) == 0


def health_ok(host: str, port: int, timeout: float = 1.0) -> bool:
    # Any HTTP response means the server is up; /api/health returns 401 to an
    # unauthenticated probe, which still proves the runtime is listening.
    try:
        conn = http.client.HTTPConnection(host, port, timeout=timeout)
        conn.request("GET", HEALTH_PATH)
        response = conn.getresponse()
        response.read()
        conn.close()
        return True
    except (OSError, http.client.HTTPException):
        return False


def read_pid() -> int | None:
    if not PID_FILE.exists():
        return None
    try:
        return int(PID_FILE.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


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
    if not VENV_PYTHON.is_file():
        print("[工作台] 未找到项目独立 Python 环境：", VENV_PYTHON)
        print("[工作台] 请先在项目 .venv 中准备依赖，不要使用 ComfyUI 整合包的 Python。")
        return 1

    existing_pid = read_pid()
    if existing_pid and pid_alive(existing_pid) and port_in_use(HOST, PORT):
        print(f"[工作台] 已有实例在运行（PID {existing_pid}，端口 {PORT}）。")
        if OPEN_BROWSER:
            import webbrowser

            webbrowser.open(f"http://{HOST}:{PORT}")
        return 0

    if port_in_use(HOST, PORT):
        print(f"[工作台] 端口 {PORT} 已被其他程序占用，无法启动工作台。")
        print("[工作台] 请关闭占用该端口的程序后重试；本脚本不会自动结束其他进程。")
        return 1

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    # Bootstrap token is generated per launch and kept in this process only;
    # it is never written into the frontend build or committed.
    if not env.get("WORKBENCH_SESSION_TOKEN"):
        env["WORKBENCH_SESSION_TOKEN"] = secrets.token_urlsafe(32)

    print(f"[工作台] 正在启动本地服务：http://{HOST}:{PORT}")

    # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP so the backend keeps running
    # after this launcher returns; the PID file records the tracked root.
    creation_flags = 0x00000008 | 0x00000200
    proc = subprocess.Popen(
        [
            str(VENV_PYTHON),
            "-m",
            "uvicorn",
            "main:app",
            "--host",
            HOST,
            "--port",
            str(PORT),
        ],
        cwd=str(BACKEND_DIR),
        env=env,
        creationflags=creation_flags,
        close_fds=True,
    )

    PID_FILE.write_text(str(proc.pid), encoding="utf-8")

    ready = False
    for _ in range(30):
        if proc.poll() is not None:
            print("[工作台] 服务进程已退出，启动失败。请查看上方错误信息。")
            PID_FILE.unlink(missing_ok=True)
            return 1
        if health_ok(HOST, PORT):
            ready = True
            break
        time.sleep(0.5)

    if not ready:
        print("[工作台] 健康检查超时，服务未在预期时间内就绪。")
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
