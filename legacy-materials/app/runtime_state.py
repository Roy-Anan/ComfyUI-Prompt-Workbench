# -*- coding: utf-8 -*-
"""阶段 7：运行状态登记。

服务端用它回答“现在在干什么、卡在哪一步、上一次结果如何”，
`/api/runtime` 和页面顶部运行条都读这里。
"""

from __future__ import annotations

import threading
import time
from datetime import datetime


def _now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


class RuntimeState:
    KINDS = ("chat", "generate")

    def __init__(self):
        self.started_monotonic = time.monotonic()
        self.started_at = _now_iso()
        self._lock = threading.RLock()
        self._tasks = {kind: None for kind in self.KINDS}
        self._last = {kind: None for kind in self.KINDS}
        self._counters = {"chat": 0, "generate": 0, "errors": 0}
        self._last_error = None

    # ------------------------------------------------------------ 任务
    def begin(self, kind, **info):
        if kind not in self._tasks:
            raise ValueError("未知任务类型：%s" % kind)
        with self._lock:
            task = {"kind": kind, "stage": "开始", "started_at": _now_iso(),
                    "started_monotonic": time.monotonic(), "detail": ""}
            task.update({k: v for k, v in info.items() if v is not None})
            self._tasks[kind] = task
            return dict(task)

    def update(self, kind, stage=None, **info):
        with self._lock:
            task = self._tasks.get(kind)
            if task is None:
                return None
            if stage:
                task["stage"] = str(stage)[:80]
            for key, val in info.items():
                if val is not None:
                    task[key] = val
            task["updated_at"] = _now_iso()
            return dict(task)

    def end(self, kind, outcome="ok", error="", **info):
        with self._lock:
            task = self._tasks.get(kind)
            finished = dict(task) if task else {"kind": kind, "started_at": _now_iso(),
                                                "started_monotonic": time.monotonic()}
            finished.update({k: v for k, v in info.items() if v is not None})
            finished["outcome"] = outcome
            finished["error"] = str(error or "")[:800]
            finished["finished_at"] = _now_iso()
            try:
                finished["elapsed_sec"] = round(
                    time.monotonic() - float(finished.get("started_monotonic") or 0), 1)
            except Exception:
                finished["elapsed_sec"] = None
            finished.pop("started_monotonic", None)
            self._last[kind] = finished
            self._tasks[kind] = None
            self._counters[kind] = self._counters.get(kind, 0) + 1
            if outcome != "ok":
                self._counters["errors"] = self._counters.get("errors", 0) + 1
                self._last_error = {"at": finished["finished_at"], "kind": kind,
                                    "message": finished["error"] or "任务失败"}
            return dict(finished)

    def mark_error(self, kind, message, **info):
        with self._lock:
            self._counters["errors"] = self._counters.get("errors", 0) + 1
            self._last_error = {"at": _now_iso(), "kind": kind,
                                "message": str(message or "未知错误")[:800]}
            if info:
                self._last_error["detail"] = {k: v for k, v in info.items() if v}

    # ------------------------------------------------------------ 查询
    def _task_public(self, task):
        if not task:
            return None
        item = dict(task)
        item.pop("started_monotonic", None)
        if not item.get("elapsed_sec"):
            try:
                item["elapsed_sec"] = round(
                    time.monotonic() - float(task.get("started_monotonic") or 0), 1)
            except Exception:
                item["elapsed_sec"] = None
        return item

    def snapshot(self):
        with self._lock:
            busy = {kind: self._tasks[kind] is not None for kind in self.KINDS}
            return {
                "started_at": self.started_at,
                "uptime_sec": round(time.monotonic() - self.started_monotonic, 1),
                "busy": busy,
                "active": {kind: self._task_public(self._tasks[kind]) for kind in self.KINDS},
                "last": {kind: dict(self._last[kind]) if self._last[kind] else None
                         for kind in self.KINDS},
                "counters": dict(self._counters),
                "last_error": dict(self._last_error) if self._last_error else None,
            }
