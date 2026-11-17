# -*- coding: utf-8 -*-
"""阶段 7：工作台运行日志。

- 写 `logs\\workbench.log`，超过 max_bytes 自动滚动，保留 backup_count 份；
- 同时在内存里留最近 memory 条，给 `/api/logs` 和页面日志面板用；
- 只记操作与结果，不记提示词 / 对话正文，避免把用户内容重复落一份。
"""

from __future__ import annotations

import json
import os
import threading
from collections import deque
from datetime import datetime

LEVELS = ("debug", "info", "warn", "error")
_ORDER = {name: i for i, name in enumerate(LEVELS)}


class WorkbenchLog:
    def __init__(self, base_dir, max_bytes=2 * 1024 * 1024, backup_count=3, memory=600):
        self.base_dir = os.path.abspath(base_dir)
        self.dir = os.path.join(self.base_dir, "logs")
        self.path = os.path.join(self.dir, "workbench.log")
        self.max_bytes = int(max_bytes)
        self.backup_count = int(backup_count)
        os.makedirs(self.dir, exist_ok=True)
        self._entries = deque(maxlen=int(memory))
        self._lock = threading.RLock()
        self._last_error = None
        self._load_tail()

    def _load_tail(self):
        """重启后把文件末尾的日志读回内存，页面不会只剩“启动”一条。"""
        if not os.path.isfile(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except Exception:
                        continue
                    if not isinstance(entry, dict) or "message" not in entry:
                        continue
                    self._entries.append(entry)
                    if entry.get("level") == "error":
                        self._last_error = entry
        except OSError:
            pass

    # ------------------------------------------------------------ 写入
    def log(self, level, scope, message, **fields):
        level = str(level or "info").lower()
        if level not in _ORDER:
            level = "info"
        entry = {
            "ts": datetime.now().astimezone().isoformat(timespec="seconds"),
            "level": level,
            "scope": str(scope or "app")[:40],
            "message": str(message or "")[:2000],
        }
        clean = {}
        for key, val in (fields or {}).items():
            if val is None:
                continue
            if isinstance(val, (str, int, float, bool)):
                clean[str(key)[:40]] = val if not isinstance(val, str) else val[:1200]
            else:
                try:
                    clean[str(key)[:40]] = json.dumps(val, ensure_ascii=False)[:1200]
                except Exception:
                    clean[str(key)[:40]] = str(val)[:1200]
        if clean:
            entry["fields"] = clean

        with self._lock:
            self._entries.append(entry)
            if level == "error":
                self._last_error = entry
            try:
                self._rotate_if_needed()
                with open(self.path, "a", encoding="utf-8", newline="\n") as fh:
                    fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
            except Exception:
                pass
        return entry

    def debug(self, scope, message, **fields):
        return self.log("debug", scope, message, **fields)

    def info(self, scope, message, **fields):
        return self.log("info", scope, message, **fields)

    def warn(self, scope, message, **fields):
        return self.log("warn", scope, message, **fields)

    def error(self, scope, message, **fields):
        return self.log("error", scope, message, **fields)

    def _rotate_if_needed(self):
        try:
            if not os.path.isfile(self.path) or os.path.getsize(self.path) < self.max_bytes:
                return
        except OSError:
            return
        for index in range(self.backup_count, 1, -1):
            src = self.path + ".%d" % (index - 1)
            dst = self.path + ".%d" % index
            if os.path.isfile(src):
                try:
                    os.replace(src, dst)
                except OSError:
                    pass
        try:
            os.replace(self.path, self.path + ".1")
        except OSError:
            pass

    # ------------------------------------------------------------ 查询
    def recent(self, limit=100, level=None):
        try:
            limit = max(1, min(int(limit), 600))
        except (TypeError, ValueError):
            limit = 100
        floor = _ORDER.get(str(level or "").lower())
        with self._lock:
            items = list(self._entries)
        if floor is not None:
            items = [e for e in items if _ORDER.get(e["level"], 0) >= floor]
        return list(reversed(items[-limit:]))

    def last_error(self):
        with self._lock:
            return dict(self._last_error) if self._last_error else None

    def files(self):
        out = []
        for suffix in [""] + [".%d" % i for i in range(1, self.backup_count + 1)]:
            path = self.path + suffix
            if os.path.isfile(path):
                try:
                    out.append({"name": os.path.basename(path),
                                "bytes": os.path.getsize(path),
                                "mtime": datetime.fromtimestamp(
                                    os.path.getmtime(path)).astimezone().isoformat(
                                        timespec="seconds")})
                except OSError:
                    pass
        return out

    def details(self):
        """日志文件与目录的元信息（给 /api/settings、/api/logs 用）。"""
        return {"path": self.path, "dir": self.dir, "files": self.files(),
                "max_bytes": self.max_bytes, "backup_count": self.backup_count}

    def export_text(self, limit=200, level=None):
        entries = self.recent(limit=limit, level=level)
        lines = []
        for entry in reversed(entries):
            fields = entry.get("fields") or {}
            extra = (" | " + json.dumps(fields, ensure_ascii=False)) if fields else ""
            lines.append("%s %-5s [%s] %s%s" % (entry["ts"], entry["level"],
                                               entry["scope"], entry["message"], extra))
        return "\n".join(lines) + ("\n" if lines else "")
