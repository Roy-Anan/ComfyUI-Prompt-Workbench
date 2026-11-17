"""Stop the workbench local Web runtime started by the launcher.

Only the PID recorded in .workbench.pid (and its direct child uvicorn worker)
is terminated. The stopper never kills Python processes by name, and it does
not touch Ollama, ComfyUI, or any other Python service.
"""

from __future__ import annotations

import ctypes
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PID_FILE = REPO_ROOT / ".workbench.pid"

kernel32 = ctypes.windll.kernel32


def pid_alive(pid: int) -> bool:
    handle = kernel32.OpenProcess(0x1000, False, pid)
    if not handle:
        return False
    exit_code = ctypes.c_ulong()
    alive = kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
    kernel32.CloseHandle(handle)
    return bool(alive) and exit_code.value == 259


def child_pids(parent_pid: int) -> list[int]:
    """Direct children of the recorded workbench root via CIM."""
    import subprocess

    try:
        output = subprocess.check_output(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"Get-CimInstance Win32_Process -Filter "
                f'"ParentProcessId={parent_pid}" | '
                "Select-Object -ExpandProperty ProcessId",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return []

    children: list[int] = []
    for line in output.splitlines():
        line = line.strip()
        if line.isdigit():
            children.append(int(line))
    return children


def terminate(pid: int) -> bool:
    handle = kernel32.OpenProcess(0x0001, False, pid)  # PROCESS_TERMINATE
    if not handle:
        return False
    ok = kernel32.TerminateProcess(handle, 0)
    kernel32.CloseHandle(handle)
    return bool(ok)


def main() -> int:
    if not PID_FILE.exists():
        print("[工作台] 未找到运行记录，工作台可能已经停止。")
        return 0

    try:
        root_pid = int(PID_FILE.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        print("[工作台] 运行记录损坏，未执行结束操作。")
        return 1

    if not pid_alive(root_pid):
        print(f"[工作台] 记录中的进程 {root_pid} 已退出，清理运行记录。")
        PID_FILE.unlink(missing_ok=True)
        return 0

    targets = [root_pid, *child_pids(root_pid)]
    for pid in targets:
        if pid_alive(pid):
            terminate(pid)

    stopped = False
    for _ in range(10):
        if not any(pid_alive(pid) for pid in targets):
            stopped = True
            break
        time.sleep(0.3)

    if not stopped:
        print(f"[工作台] 进程 {root_pid} 仍在运行，请手动确认。")
        return 1

    PID_FILE.unlink(missing_ok=True)
    print(f"[工作台] 已停止工作台进程 {root_pid}（含其子进程），未影响其他服务。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
