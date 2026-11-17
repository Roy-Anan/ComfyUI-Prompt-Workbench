"""Stop the workbench local Web runtime started by the launcher.

Safety model:
  * The recorded PID is never trusted alone. Before terminating, the stopper
    verifies process identity against several stable attributes: executable
    path, command line, working directory and the workbench Python venv.
  * If identity cannot be confirmed (PID reused by another program, missing
    attributes, or a mismatch), the process is left alone and a warning is
    printed for manual review.
  * The whole workbench process tree (root plus recursive descendants) is
    terminated. Python processes are never killed by name, and Ollama,
    ComfyUI, or any other Python service is untouched.
"""

from __future__ import annotations

import ctypes
import json
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PID_FILE = REPO_ROOT / ".workbench.pid"
RUNTIME_RECORD_FILE = REPO_ROOT / ".workbench-runtime.json"
VENV_PYTHON = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
BACKEND_DIR = REPO_ROOT / "backend"
APP_ID = "ComfyUI-Prompt-Workbench"
APP_MARKER = "uvicorn"  # Command-line marker for the tracked backend process.

kernel32 = ctypes.windll.kernel32


def pid_alive(pid: int) -> bool:
    handle = kernel32.OpenProcess(0x1000, False, pid)
    if not handle:
        return False
    exit_code = ctypes.c_ulong()
    alive = kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
    kernel32.CloseHandle(handle)
    return bool(alive) and exit_code.value == 259


def _process_info(pid: int) -> dict[str, str] | None:
    """Read stable identity attributes for a PID via CIM.

    Returns a dict with ExecutablePath, CommandLine, CreationDate,
    WorkingDirectory (when available), or None when the process is gone.
    """
    ps = (
        "Get-CimInstance Win32_Process -Filter "
        f'"ProcessId={pid}" | '
        "Select-Object ProcessId,ExecutablePath,CommandLine,"
        "@{n='CreationDate';e={$_.CreationDate.ToString(\"yyyy-MM-ddTHH:mm:ss.ffffffZ\")}},"
        "WorkingDirectory | "
        "ConvertTo-Json -Compress"
    )
    try:
        output = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", ps],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return None

    output = output.strip()
    if not output:
        return None
    try:
        data = json.loads(output)
    except ValueError:
        return None
    if isinstance(data, list):
        data = data[0] if data else {}
    return data if isinstance(data, dict) else None


def _normalized(path: str | None) -> str:
    if not path:
        return ""
    return str(Path(path)).lower().replace("/", "\\")


def read_runtime_record() -> dict | None:
    """Read the structured launcher record; None when missing/corrupt."""
    if not RUNTIME_RECORD_FILE.exists():
        return None
    try:
        data = json.loads(RUNTIME_RECORD_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _creation_date_equal(a: str | None, b: str | None) -> bool:
    """Compare CreationDate instants; a missing side fails closed."""
    if not a or not b:
        return False
    return a.strip() == b.strip()


def _health_instance(host: str | None, port: int | None) -> str | None:
    """Read the running backend's instance id from its loopback health probe."""
    if not host or not port:
        return None
    try:
        import http.client

        conn = http.client.HTTPConnection(str(host), int(port), timeout=1.0)
        conn.request("GET", "/api/health")
        response = conn.getresponse()
        body = response.read()
        conn.close()
        payload = json.loads(body.decode("utf-8"))
    except (OSError, http.client.HTTPException, ValueError, UnicodeDecodeError):
        return None
    value = payload.get("instance_id")
    return value if isinstance(value, str) and value else None


def identify_workbench(pid: int, record: dict | None = None) -> tuple[bool, str]:
    """Confirm the PID belongs to this workbench.

    The PID alone is never trusted. We compare the live process against the
    structured launcher record on executable path, working directory, command
    line, recorded instance id and process creation time. Any missing critical
    attribute or mismatch fails closed: the process is left alone.
    """
    info = _process_info(pid)
    if info is None:
        return False, "无法读取进程身份信息（进程可能已退出）"

    exe = _normalized(info.get("ExecutablePath"))
    cmd = (info.get("CommandLine") or "").lower()
    creation = info.get("CreationDate")
    venv = _normalized(str(VENV_PYTHON))

    if not exe:
        return False, "缺少可执行路径，身份无法确认"
    if exe != venv:
        return False, f"可执行路径不属于项目 .venv：{exe}"
    if APP_MARKER not in cmd or "main:app" not in cmd:
        return False, "命令行不是本工作台的 uvicorn 后端"
    if BACKEND_DIR.name not in cmd and str(REPO_ROOT).lower() not in cmd:
        return False, "命令行未指向项目后端目录"

    # Structured record is required for the stricter identity comparison.
    if not record:
        return False, "缺少结构化运行记录，身份无法确认"

    if record.get("app_id") != APP_ID:
        return False, "记录中的应用标识与本工作台不匹配"

    record_instance = record.get("instance_id")
    if not record_instance:
        return False, "记录缺少本次启动实例标识，身份无法确认"

    live_instance = _health_instance(record.get("host"), record.get("port"))
    if not live_instance:
        return False, "无法读取活动进程实例标识，身份无法确认"
    if live_instance != record_instance:
        return False, "实例标识与本次启动记录不一致"

    record_pid = record.get("pid")
    if record_pid is not None and int(record_pid) != pid:
        return False, f"记录 PID（{record_pid}）与当前 PID（{pid}）不一致"

    record_exe = _normalized(record.get("executable_path"))
    if record_exe and record_exe != exe:
        return False, f"可执行路径与记录不符：{exe} != {record_exe}"

    record_cwd = _normalized(record.get("working_directory"))
    live_cwd = _normalized(info.get("WorkingDirectory"))
    if record_cwd and live_cwd and record_cwd != live_cwd:
        return False, f"工作目录与记录不符：{live_cwd} != {record_cwd}"

    record_cmd = record.get("command_line")
    if isinstance(record_cmd, list):
        record_parts = [_normalized(part) for part in record_cmd if part]
    else:
        record_parts = [_normalized(record_cmd)] if record_cmd else []
    live_parts = [part for part in cmd.split() if part]
    if record_parts and not all(any(part in live for live in live_parts) for part in record_parts):
        return False, "命令行参数与记录不符"

    if not _creation_date_equal(record.get("creation_date"), creation):
        return False, "进程启动时间与记录不一致（PID 可能已被复用）"

    return True, "身份匹配"


def child_pids(parent_pid: int) -> list[int]:
    """Direct children of the recorded workbench root via CIM."""
    try:
        output = subprocess.check_output(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_Process -Filter "
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


def descendant_pids(root_pid: int) -> list[int]:
    """Recursively collect the full descendant PID set."""
    seen: set[int] = set()
    queue = [root_pid]
    while queue:
        parent = queue.pop()
        for child in child_pids(parent):
            if child not in seen:
                seen.add(child)
                queue.append(child)
    return sorted(seen)


def terminate(pid: int) -> bool:
    handle = kernel32.OpenProcess(0x0001, False, pid)  # PROCESS_TERMINATE
    if not handle:
        return False
    ok = kernel32.TerminateProcess(handle, 0)
    kernel32.CloseHandle(handle)
    return bool(ok)


def clear_runtime_record() -> None:
    PID_FILE.unlink(missing_ok=True)
    RUNTIME_RECORD_FILE.unlink(missing_ok=True)


def main() -> int:
    record = read_runtime_record()

    if record is None:
        # No structured record: either already stopped, or the record is
        # corrupt. Either way fail closed — do not kill a PID we cannot verify.
        if RUNTIME_RECORD_FILE.exists():
            print("[工作台] 运行记录损坏，未执行结束操作，请人工检查。")
            return 1
        if not PID_FILE.exists():
            print("[工作台] 未找到运行记录，工作台可能已经停止。")
            return 0
        # Only a legacy plain PID file remains; without identity evidence we
        # do not terminate.
        print("[工作台] 缺少结构化运行记录，未执行结束操作，请人工检查。")
        return 1

    try:
        root_pid = int(record.get("pid"))
    except (TypeError, ValueError):
        print("[工作台] 运行记录中的 PID 无效，未执行结束操作。")
        return 1

    if not pid_alive(root_pid):
        print(f"[工作台] 记录中的进程 {root_pid} 已退出，清理运行记录。")
        clear_runtime_record()
        return 0

    matches, reason = identify_workbench(root_pid, record)
    if not matches:
        print(
            f"[工作台] 进程 {root_pid} 身份与本工作台不匹配（{reason}）。"
            "为避免误杀其他程序，已保留现场，未结束任何进程，请人工检查。"
        )
        return 1

    targets = [root_pid, *descendant_pids(root_pid)]
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

    clear_runtime_record()
    print(f"[工作台] 已停止工作台进程 {root_pid}（含其子进程），未影响其他服务。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
