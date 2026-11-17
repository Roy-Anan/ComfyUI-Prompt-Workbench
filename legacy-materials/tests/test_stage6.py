# -*- coding: utf-8 -*-
"""阶段 6 测试：显存状态机（检测 → 卸载 → 显存等待 → 释放 → 恢复 → 回滚）。

不碰真 GPU / 真 Ollama（真链路在 tests/smoke_server.py 里跑）。
运行：python -m unittest discover -s tests -v
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from app import history_store, vram_manager  # noqa: E402
from app.vram_manager import VramSession  # noqa: E402


class FakeOllama:
    def __init__(self, loaded=None, fail_unload=False, fail_preload=False):
        self.models = list(loaded or [])
        self.fail_unload = fail_unload
        self.fail_preload = fail_preload
        self.calls = []

    def version(self):
        self.calls.append("version")
        return {"ok": True, "data": {"version": "0.40.15"}}

    def loaded_models(self):
        self.calls.append("loaded_models")
        return {"ok": True, "models": [dict(m) for m in self.models]}

    def unload(self):
        self.calls.append("unload")
        if self.fail_unload:
            return {"ok": False, "error": "keep_alive=0 失败"}
        self.models = []
        return {"ok": True}

    def preload(self, model=None, keep_alive=None):
        self.calls.append("preload")
        if self.fail_preload:
            return {"ok": False, "error": "加载失败"}
        self.models = [{"name": "comfyui-prompt:v1", "size_vram": 6064292494}]
        return {"ok": True}


class FakeComfy:
    def __init__(self, free_ok=True):
        self.free_ok = free_ok
        self.freed = 0

    def system_stats(self):
        return {"ok": True, "data": {"system": {"comfyui_version": "0.30.2"}}}

    def queue_state(self):
        return {"running": [], "pending": []}

    def free(self, unload_models=True, free_memory=True):
        self.freed += 1
        return {"ok": self.free_ok}


class GpuScript:
    def __init__(self, values):
        self.values = [v if isinstance(v, dict) else {"ok": True, "used_mb": v,
                                                      "free_mb": 8188 - v, "total_mb": 8188}
                       for v in values]
        self.i = 0

    def __call__(self):
        value = self.values[min(self.i, len(self.values) - 1)]
        self.i += 1
        return dict(value)


class FakeHistory:
    def __init__(self, messages=4, exists=True):
        self.messages = [{"role": "user" if i % 2 == 0 else "assistant", "content": "m%d" % i}
                         for i in range(messages)]
        self.exists = exists
        self.saved = 0

    def save_context_snapshot(self, cid, extra=None):
        if not self.exists:
            return None
        self.saved += 1
        return {"path": "history/contexts/%s.json" % cid, "name": "%s.json" % cid,
                "message_count": len(self.messages)}

    def load(self, cid):
        if not self.exists:
            return None
        return {"conversation_id": cid, "messages": self.messages}


def fake_sleep(_seconds):
    return None


def loaded_model(name="comfyui-prompt:v1", size=6064292494):
    return {"name": name, "size_vram": size}


class GpuMemoryTest(unittest.TestCase):
    def test_parse_nvidia_smi(self):
        proc = mock.Mock(returncode=0, stdout="NVIDIA GeForce RTX 4060 Laptop GPU, 8188, 4766, 3191\n",
                         stderr="")
        with mock.patch("subprocess.run", return_value=proc) as run:
            gpu = vram_manager.gpu_memory()
        self.assertTrue(gpu["ok"])
        self.assertEqual(gpu["total_mb"], 8188)
        self.assertEqual(gpu["used_mb"], 4766)
        self.assertEqual(gpu["free_mb"], 3191)
        self.assertEqual(gpu["total_gb"], 8.0)
        self.assertIn("nvidia-smi", run.call_args[0][0][0])

    def test_missing_nvidia_smi_is_reported(self):
        with mock.patch("subprocess.run", side_effect=FileNotFoundError("nope")):
            gpu = vram_manager.gpu_memory()
        self.assertFalse(gpu["ok"])
        self.assertTrue(gpu["error"])

    def test_nonzero_exit(self):
        proc = mock.Mock(returncode=9, stdout="", stderr="driver mismatch")
        with mock.patch("subprocess.run", return_value=proc):
            gpu = vram_manager.gpu_memory()
        self.assertFalse(gpu["ok"])
        self.assertIn("driver", gpu["error"])


class VramSessionTest(unittest.TestCase):
    def session(self, ollama=None, comfy=None, gpu=None, history=None, **cfg):
        config = {"auto_manage": True, "min_free_mb": 4000, "wait_free_seconds": 0.3,
                  "poll_interval": 0.1, "reload_ollama": True, "unload_wait_seconds": 0.2,
                  "reload_wait_seconds": 0.2, "free_wait_seconds": 0.2}
        config.update(cfg)
        self.history = history or FakeHistory()
        return VramSession(self.history, ollama or FakeOllama(), comfy or FakeComfy(),
                           config=config, gpu_fn=gpu or GpuScript([6000]), sleep=fake_sleep)

    def names(self, summary):
        return [s["name"] for s in summary["steps"]]

    def test_disabled_does_nothing(self):
        s = self.session()
        summary = s.start("c-1", auto=False)
        self.assertFalse(summary["auto"])
        self.assertEqual(self.names(summary), ["disabled"])
        self.assertEqual(s.ollama.calls, [])

    def test_full_order_when_model_loaded(self):
        ollama = FakeOllama(loaded=[loaded_model()])
        s = self.session(ollama=ollama, gpu=GpuScript([5500, 6000]))
        summary = s.start("c-1")
        self.assertEqual(self.names(summary), ["ollama_detect", "context_snapshot",
                                               "ollama_unload", "gpu_check", "comfy_check"])
        self.assertEqual(summary["ollama_loaded_before"], ["comfyui-prompt:v1"])
        self.assertTrue(summary["steps"][2]["ok"])
        self.assertEqual(ollama.calls.count("unload"), 1)
        self.assertEqual(self.history.saved, 1)
        self.assertTrue(summary["steps"][1]["ok"])

    def test_no_model_means_no_unload(self):
        ollama = FakeOllama()
        s = self.session(ollama=ollama, gpu=GpuScript([6000]))
        summary = s.start("c-1")
        self.assertEqual(ollama.calls.count("unload"), 0)
        unload = [x for x in summary["steps"] if x["name"] == "ollama_unload"][0]
        self.assertTrue(unload["ok"])
        self.assertIn("本来没加载", unload["detail"])

    def test_waits_for_vram_to_free(self):
        gpu = GpuScript([6500, 6000, 2888])
        s = self.session(gpu=gpu)
        summary = s.start("c-1")
        check = [x for x in summary["steps"] if x["name"] == "gpu_check"][0]
        self.assertTrue(check["ok"])
        self.assertIn("等到空闲 5300", check["detail"])
        self.assertEqual(gpu.i, 3)
        self.assertFalse(summary["fatal"])

    def test_low_vram_strict_fails(self):
        s = self.session(gpu=GpuScript([6500]), strict_vram=True)
        summary = s.start("c-1")
        self.assertTrue(summary["fatal"])
        self.assertTrue(any("gpu_check" in e for e in summary["errors"]))

    def test_low_vram_non_strict_warns(self):
        s = self.session(gpu=GpuScript([6500]), strict_vram=False)
        summary = s.start("c-1")
        self.assertFalse(summary["fatal"])
        self.assertTrue(any("空闲 1688" in w for w in summary["warnings"]))

    def test_unload_failure_is_fatal(self):
        s = self.session(ollama=FakeOllama(loaded=[loaded_model()], fail_unload=True),
                         gpu=GpuScript([3000]))
        summary = s.start("c-1")
        self.assertTrue(summary["fatal"])

    def test_ollama_down_does_not_block_generation(self):
        ollama = FakeOllama()
        ollama.version = lambda: {"ok": False, "error": "connect refused"}
        ollama.loaded_models = lambda: {"ok": False, "models": [], "error": "connect refused"}
        s = self.session(ollama=ollama, gpu=GpuScript([6000]))
        summary = s.start("c-1")
        self.assertFalse(summary["fatal"])
        self.assertIn("ollama_skip", self.names(summary))

    def test_after_comfy_frees_and_measures_drop(self):
        comfy = FakeComfy()
        gpu = GpuScript([4000, 7000, 4200])
        s = self.session(comfy=comfy, gpu=gpu)
        s.start("c-1")
        summary = s.after_comfy()
        free = [x for x in summary["steps"] if x["name"] == "comfy_free"][0]
        self.assertTrue(free["ok"])
        self.assertEqual(comfy.freed, 1)
        self.assertEqual(summary["free_after"]["used_mb"], 4200)
        self.assertIn("7000 → 4200", free["detail"])

    def test_restore_reloads_and_confirms_context(self):
        ollama = FakeOllama(loaded=[loaded_model()])
        s = self.session(ollama=ollama, gpu=GpuScript([6000, 1954, 7000]))
        s.start("c-1")
        summary = s.restore()
        self.assertTrue(summary["ollama_reloaded"])
        self.assertTrue(summary["context_restored"])
        self.assertIn("ollama_reload", self.names(summary))
        self.assertIn("context_restore", self.names(summary))
        self.assertEqual(ollama.calls.count("preload"), 1)

    def test_restore_skips_reload_when_never_loaded(self):
        ollama = FakeOllama()
        s = self.session(ollama=ollama, gpu=GpuScript([6000]), reload_ollama=False)
        s.start("c-1")
        summary = s.restore()
        self.assertFalse(summary["ollama_reloaded"])
        self.assertEqual(ollama.calls.count("preload"), 0)
        self.assertTrue(summary["context_restored"])

    def test_restore_retries_reload_twice(self):
        ollama = FakeOllama(fail_preload=True)
        s = self.session(ollama=ollama, gpu=GpuScript([6000]))
        s.start("c-1")
        summary = s.restore()
        self.assertFalse(summary["ollama_reloaded"])
        self.assertEqual(ollama.calls.count("preload"), 2)
        self.assertTrue(any("没恢复" in w for w in summary["warnings"]))

    def test_abort_reloads_model_after_failure(self):
        ollama = FakeOllama(loaded=[loaded_model()])
        s = self.session(ollama=ollama, gpu=GpuScript([6000, 6000]))
        s.start("c-1")
        summary = s.abort("提交失败")
        self.assertIn("abort", self.names(summary))
        self.assertIn("rollback_reload", self.names(summary))
        self.assertTrue(summary["ollama_reloaded"])

    def test_summary_fields(self):
        s = self.session()
        summary = s.start("c-1")
        for key in ("auto", "fatal", "finished", "steps", "ollama_loaded_before",
                    "ollama_reloaded", "context_snapshot", "context_restored",
                    "vram_before", "vram_after", "warnings", "errors", "total_sec"):
            self.assertIn(key, summary)


class ContextSnapshotTest(unittest.TestCase):
    def test_snapshot_written_with_messages(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = history_store.HistoryStore(tmp)
            conv = store.create(title="快照", checkpoint="a.safetensors")
            store.append_message(conv["conversation_id"], "user", "第一条")
            store.append_message(conv["conversation_id"], "assistant", "第二条")
            snap = store.save_context_snapshot(conv["conversation_id"], {"reason": "test"})
            self.assertIsNotNone(snap)
            self.assertEqual(snap["message_count"], 2)
            path = os.path.join(tmp, snap["path"].replace("/", os.sep))
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            self.assertEqual(data["conversation_id"], conv["conversation_id"])
            self.assertEqual(len(data["messages"]), 2)
            self.assertEqual(data["reason"], "test")
            self.assertEqual(data["messages"][0]["content"], "第一条")

    def test_snapshot_missing_conversation_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = history_store.HistoryStore(tmp)
            self.assertIsNone(store.save_context_snapshot("c-不存在"))


if __name__ == "__main__":
    unittest.main()
