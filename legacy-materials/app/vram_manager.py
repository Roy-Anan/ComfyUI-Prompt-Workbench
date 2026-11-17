# -*- coding: utf-8 -*-
"""阶段 6：显存自动管理。

按计划书顺序跑一条可回放的状态机：

    Ollama 状态检测 → 保存上下文 → 卸载 Ollama → GPU 显存检测
    → ComfyUI 状态检测 → （服务端提交/轮询） → 释放 ComfyUI 模型与缓存
    → 重新加载 Ollama → 恢复上下文 → 汇总

只依赖标准库与 nvidia-smi；所有步骤都落到 `steps` 里，前端与记录可逐条查看。
"""

from __future__ import annotations

import os
import subprocess
import time
from datetime import datetime

DEFAULT_CONFIG = {
    "auto_manage": True,
    "min_free_mb": 4000,
    "wait_free_seconds": 40,
    "poll_interval": 1.0,
    "free_comfy_after": True,
    "free_wait_seconds": 20,
    "unload_wait_seconds": 20,
    "reload_ollama": True,
    "reload_wait_seconds": 15,
    "reload_keep_alive": "30m",
    "strict_vram": False,
}

_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def _now():
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def gpu_memory():
    """读 NVIDIA 显存（MB）。没有 nvidia-smi 时明确返回不可用，不编数。"""
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    candidates = [os.path.join(system_root, "System32", "nvidia-smi.exe"), "nvidia-smi"]
    last_error = ""
    for exe in candidates:
        if exe != "nvidia-smi" and not os.path.isfile(exe):
            continue
        try:
            proc = subprocess.run(
                [exe, "--query-gpu=name,memory.total,memory.used,memory.free",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=10,
                creationflags=_NO_WINDOW)
        except Exception as exc:
            last_error = "%s: %s" % (type(exc).__name__, exc)
            continue
        if proc.returncode != 0:
            last_error = (proc.stderr or proc.stdout or "").strip()[:200]
            continue
        line = (proc.stdout or "").strip().splitlines()
        if not line:
            last_error = "nvidia-smi 没有输出"
            continue
        parts = [p.strip() for p in line[0].split(",")]
        try:
            total, used, free = int(parts[1]), int(parts[2]), int(parts[3])
        except (IndexError, ValueError):
            last_error = "nvidia-smi 输出无法解析：%s" % line[0][:120]
            continue
        return {"ok": True, "name": parts[0], "total_mb": total,
                "used_mb": used, "free_mb": free,
                "used_gb": round(used / 1024.0, 2), "free_gb": round(free / 1024.0, 2),
                "total_gb": round(total / 1024.0, 2)}
    return {"ok": False, "error": last_error or "找不到 nvidia-smi"}


class VramSession:
    def __init__(self, history, ollama, comfy, config=None, gpu_fn=None, sleep=time.sleep):
        self.history = history
        self.ollama = ollama
        self.comfy = comfy
        self.cfg = dict(DEFAULT_CONFIG)
        self.cfg.update(config or {})
        self.gpu_fn = gpu_fn or gpu_memory
        self.sleep = sleep
        self._reset()

    # ---------------------------------------------------------------- 基础
    def _reset(self):
        self.steps = []
        self.errors = []
        self.warnings = []
        self.t0 = None
        self.auto = False
        self.fatal = False
        self.started = False
        self.finished = False
        self.conv_id = ""
        self.loaded_before = []
        self.snapshot = None
        self.reloaded = False
        self.context_restored = False
        self.vram_before = {}
        self.vram_after = {}
        self.free_after = {}

    def _record(self, name, ok, detail="", vram=None, extra=None):
        item = {"name": name, "ok": bool(ok), "detail": detail, "at": _now()}
        if vram:
            item["vram"] = {k: vram.get(k) for k in
                            ("used_mb", "free_mb", "total_mb") if k in vram}
        if extra:
            item.update(extra)
        self.steps.append(item)
        if not ok:
            self.errors.append("%s：%s" % (name, detail))
        return item

    def _wait_for(self, probe, timeout, interval=None):
        """反复调用 probe()，返回 (ok, 最后一次结果)。"""
        interval = interval or float(self.cfg["poll_interval"])
        deadline = time.time() + float(timeout)
        last = probe()
        while not last and time.time() < deadline:
            self.sleep(interval)
            last = probe()
        return bool(last), last

    # ---------------------------------------------------------------- 开始
    def start(self, conv_id="", auto=None):
        self._reset()
        self.t0 = time.time()
        self.conv_id = conv_id or ""
        self.auto = bool(self.cfg.get("auto_manage", True)) if auto is None else bool(auto)
        if not self.auto:
            self._record("disabled", True, "按请求跳过显存自动管理")
            return self.summary()
        self.started = True

        # 1. Ollama 状态检测
        version = self.ollama.version()
        loaded = self.ollama.loaded_models()
        self.loaded_before = loaded.get("models") or []
        self._record("ollama_detect", bool(version.get("ok")) and bool(loaded.get("ok")),
                     "版本 %s，已加载 %s" % (
                         (version.get("data") or {}).get("version", "?") if version.get("ok") else "未运行",
                         "、".join(m["name"] for m in self.loaded_before) or "无"))
        if not version.get("ok"):
            self.warnings.append("Ollama 没在运行，跳过卸载/恢复：%s" % version.get("error", ""))
            self._record("ollama_skip", True, "Ollama 不可用，本次只出图不涉及对话模型")

        # 2. 保存上下文（出图前快照，证明可恢复）
        if self.conv_id:
            self.snapshot = self.history.save_context_snapshot(
                self.conv_id, extra={"reason": "before_comfy_generation"})
            self._record("context_snapshot", bool(self.snapshot),
                         "已存 %s（%d 条消息）" % (
                             (self.snapshot or {}).get("name", "?"),
                             (self.snapshot or {}).get("message_count", 0)))
            if not self.snapshot:
                self.warnings.append("对话不存在，未保存上下文快照")
        else:
            self._record("context_snapshot", True, "本次出图没有挂对话，跳过快照")

        # 3. 卸载 Ollama
        def remaining_models():
            state = self.ollama.loaded_models()
            return None if (state.get("models") or []) else state

        if self.loaded_before:
            first = self.ollama.unload()
            ok, after = self._wait_for(
                remaining_models,
                timeout=float(self.cfg.get("unload_wait_seconds") or 20))
            remain = (after or {}).get("models") or []
            size = sum(int(m.get("size_vram") or 0) for m in self.loaded_before)
            self._record("ollama_unload", bool(first.get("ok")) and ok,
                         "卸载 %s（显存 %d MB）→ 剩余 %s" % (
                             "、".join(m["name"] for m in self.loaded_before),
                             round(size / 1024 / 1024),
                             "、".join(m["name"] for m in remain) or "无"))
            if not ok:
                self.fatal = True
        else:
            self._record("ollama_unload", True, "Ollama 本来没加载模型")

        # 4. GPU 显存检测（不够就等，超时按配置决定是否硬失败）
        self.vram_before = self.gpu_fn()
        need = int(self.cfg.get("min_free_mb") or 0)
        if self.vram_before.get("ok") and self.vram_before.get("free_mb", 0) < need:
            patience = float(self.cfg.get("wait_free_seconds") or 0)

            def enough_free():
                state = self.gpu_fn()
                if state.get("ok") and state.get("free_mb", 0) >= need:
                    return state
                return None

            ok, last = self._wait_for(enough_free, timeout=patience)
            self.vram_before = last if isinstance(last, dict) else self.vram_before
            if not ok:
                msg = "空闲 %s MB < 需要 %s MB（已等 %s 秒）" % (
                    self.vram_before.get("free_mb"), need, patience)
                if self.cfg.get("strict_vram"):
                    self.fatal = True
                    self._record("gpu_check", False, msg)
                else:
                    self.warnings.append(msg)
                    self._record("gpu_check", True, msg + "，继续尝试（非严格模式）")
            else:
                self._record("gpu_check", True, "等到空闲 %s MB（需要 %s MB）" % (
                    self.vram_before.get("free_mb"), need))
        else:
            self._record("gpu_check", bool(self.vram_before.get("ok")),
                         ("空闲 %s / 总共 %s MB" % (
                             self.vram_before.get("free_mb"),
                             self.vram_before.get("total_mb")))
                         if self.vram_before.get("ok")
                         else "读不到显存：%s" % self.vram_before.get("error"))
            if not self.vram_before.get("ok"):
                self.warnings.append("读不到显存（nvidia-smi 不可用），跳过容量判断")

        # 5. ComfyUI 状态检测
        stats = self.comfy.system_stats()
        queue = self.comfy.queue_state()
        version_c = ((stats.get("data") or {}).get("system") or {}).get("comfyui_version", "") \
            if stats.get("ok") else ""
        self._record("comfy_check", bool(stats.get("ok")),
                     "版本 %s，队列 %s/%s" % (version_c or "?",
                                            len(queue.get("running") or []),
                                            len(queue.get("pending") or [])))
        if not stats.get("ok"):
            self.fatal = True
        return self.summary()

    # ---------------------------------------------------------------- 出图后
    def after_comfy(self):
        if not self.auto or not self.started:
            return self.summary()
        if not self.cfg.get("free_comfy_after", True):
            self._record("comfy_free", True, "配置为不释放")
            return self.summary()
        before = self.gpu_fn()
        result = self.comfy.free(unload_models=True, free_memory=True)
        dropped = False
        if before.get("ok"):
            deadline = time.time() + float(self.cfg.get("free_wait_seconds") or 0)
            last = before
            while time.time() < deadline:
                self.sleep(float(self.cfg.get("poll_interval") or 1))
                last = self.gpu_fn()
                if last.get("ok") and last.get("used_mb", 1 << 30) < before.get("used_mb", 0):
                    dropped = True
                    break
            self.free_after = last
        self._record("comfy_free", bool(result.get("ok")),
                     "已请求 /free（unload_models+free_memory）" +
                     ("，显存 %s → %s MB" % (before.get("used_mb"), self.free_after.get("used_mb"))
                      if dropped else ""),
                     vram=self.free_after)
        return self.summary()

    # ---------------------------------------------------------------- 恢复
    def restore(self):
        if not self.auto or not self.started:
            return self.summary()
        should_reload = bool(self.loaded_before) or bool(self.cfg.get("reload_ollama", True))
        if should_reload:
            keep_alive = str(self.cfg.get("reload_keep_alive") or "30m")
            attempt = 0
            loaded_now = {"models": []}

            def has_models():
                state = self.ollama.loaded_models()
                return state if state.get("models") else None

            while attempt < 2:
                attempt += 1
                self.ollama.preload(keep_alive=keep_alive)
                ok, loaded_now = self._wait_for(
                    has_models,
                    timeout=float(self.cfg.get("reload_wait_seconds") or 15))
                if ok:
                    break
                self.sleep(2)
            names = [m.get("name") for m in (loaded_now or {}).get("models") or []]
            self.reloaded = bool(names)
            self._record("ollama_reload", self.reloaded,
                         "已加载 %s（keep_alive=%s，第 %d 次）" % (
                             "、".join(names) or "无", keep_alive, attempt),
                         extra={"attempts": attempt})
            if not self.reloaded:
                self.warnings.append("Ollama 模型没恢复，对话可能暂时用不了")
        else:
            self._record("ollama_reload", True, "原先没加载模型，跳过")

        # 恢复历史上下文：核对快照与磁盘上的对话
        if self.snapshot:
            conv = self.history.load(self.conv_id)
            now_count = len((conv or {}).get("messages") or [])
            ok_ctx = conv is not None and now_count >= int(self.snapshot.get("message_count") or 0)
            self.context_restored = ok_ctx
            self._record("context_restore", ok_ctx,
                         "对话 %s 现有 %d 条（快照 %d 条），可继续续聊" % (
                             self.conv_id, now_count, self.snapshot.get("message_count", 0)))
        else:
            self._record("context_restore", True, "没有挂对话，跳过")

        self.vram_after = self.gpu_fn()
        self._record("gpu_after", bool(self.vram_after.get("ok")),
                     "空闲 %s / 总共 %s MB" % (self.vram_after.get("free_mb"),
                                              self.vram_after.get("total_mb"))
                     if self.vram_after.get("ok") else "读不到显存",
                     vram=self.vram_after)
        self.finished = True
        return self.summary()

    # ---------------------------------------------------------------- 回滚
    def abort(self, reason=""):
        if not self.auto or not self.started:
            return self.summary()
        self._record("abort", True, reason or "出图链路失败，执行回滚")
        if self.loaded_before and not self.reloaded:
            keep_alive = str(self.cfg.get("reload_keep_alive") or "30m")

            def has_models():
                state = self.ollama.loaded_models()
                return state if state.get("models") else None

            self.ollama.preload(keep_alive=keep_alive)
            ok, loaded_now = self._wait_for(
                has_models,
                timeout=float(self.cfg.get("reload_wait_seconds") or 15))
            self.reloaded = bool(ok)
            self._record("rollback_reload", self.reloaded,
                         "回滚时重新加载 %s" % ("成功" if self.reloaded else "失败"))
        return self.summary()

    # ---------------------------------------------------------------- 汇总
    def summary(self):
        elapsed = round(time.time() - self.t0, 1) if self.t0 else 0
        return {
            "auto": self.auto,
            "fatal": self.fatal,
            "finished": self.finished,
            "steps": self.steps,
            "ollama_loaded_before": [m.get("name") for m in self.loaded_before],
            "ollama_reloaded": self.reloaded,
            "context_snapshot": (self.snapshot or {}).get("path", ""),
            "context_message_count": (self.snapshot or {}).get("message_count"),
            "context_restored": self.context_restored,
            "vram_before": self.vram_before,
            "vram_after": self.vram_after,
            "free_after": self.free_after,
            "warnings": self.warnings,
            "errors": self.errors,
            "total_sec": elapsed,
        }
