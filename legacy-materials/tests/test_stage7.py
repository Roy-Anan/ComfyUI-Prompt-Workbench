# -*- coding: utf-8 -*-
"""阶段 7 测试：运行日志 / 运行状态 / 备份 / 设置白名单。

全部在临时目录里跑，不碰真实 history、settings、backups、logs。
运行：python -m unittest discover -s tests -v
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
import zipfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from app.backup import BackupManager  # noqa: E402
from app.runtime_state import RuntimeState  # noqa: E402
from app.settings_store import SettingsStore, validate_patch  # noqa: E402
from app.workbench_log import WorkbenchLog  # noqa: E402


class Stage7LogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="wb_log_")
        self.log = WorkbenchLog(self.tmp, max_bytes=1024 * 1024, memory=50)
        self.path = os.path.join(self.tmp, "logs", "workbench.log")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_json_line_and_recent(self):
        self.log.info("server", "工作台启动", version="2.0")
        self.log.error("generate", "出图失败", reason="vram")
        with open(self.path, encoding="utf-8") as fh:
            lines = [json.loads(x) for x in fh.read().splitlines()]
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0]["level"], "info")
        self.assertIn("message", lines[1])
        self.assertIn("fields", lines[1])
        recent = self.log.recent(limit=2)
        self.assertEqual(recent[0]["level"], "error")  # 新的在前

    def test_level_filter(self):
        self.log.debug("a", "debug")
        self.log.info("b", "info")
        self.log.warn("c", "warn")
        self.log.error("d", "error")
        self.assertEqual(len(self.log.recent(level="warn")), 2)
        self.assertEqual(len(self.log.recent(level="error")), 1)
        self.assertEqual(len(self.log.recent(level="info")), 3)

    def test_restart_reads_tail(self):
        self.log.info("server", "一")
        self.log.info("server", "二")
        reloaded = WorkbenchLog(self.tmp, max_bytes=1024 * 1024, memory=50)
        messages = [e["message"] for e in reloaded.recent(limit=10)]
        self.assertEqual(messages, ["二", "一"])

    def test_rotation(self):
        small = WorkbenchLog(self.tmp, max_bytes=200, backup_count=2, memory=10)
        for i in range(8):
            small.info("test", "第 %d 条日志，用来把文件撑过阈值 %s" % (i, "x" * 20))
        self.assertTrue(os.path.isfile(self.path))
        self.assertTrue(os.path.isfile(self.path + ".1"))
        self.assertFalse(os.path.isfile(self.path + ".3"))

    def test_last_error_and_export(self):
        self.log.error("client", "页面异常", url="/")
        last = self.log.last_error()
        self.assertEqual(last["message"], "页面异常")
        text = self.log.export_text(limit=10)
        self.assertIn("页面异常", text)
        self.assertIn("client", text)

    def test_info_has_files(self):
        self.log.info("server", "启动")
        info = self.log.details()
        self.assertEqual(info["path"], self.path)
        self.assertTrue(info["files"])
        self.assertGreater(info["files"][0]["bytes"], 0)


class Stage7RuntimeTests(unittest.TestCase):
    def test_begin_update_end_and_snapshot(self):
        rt = RuntimeState()
        rt.begin("generate", generation_id="g-1")
        rt.update("generate", stage="等待执行", progress=0.5)
        snap = rt.snapshot()
        self.assertTrue(snap["busy"]["generate"])
        self.assertEqual(snap["active"]["generate"]["stage"], "等待执行")
        self.assertIn("uptime_sec", snap)

        last = rt.end("generate", "ok", duration_sec=12)
        self.assertEqual(last["outcome"], "ok")
        self.assertIsInstance(last["elapsed_sec"], float)
        snap = rt.snapshot()
        self.assertFalse(snap["busy"]["generate"])
        self.assertEqual(snap["counters"]["generate"], 1)
        self.assertEqual(snap["counters"]["errors"], 0)
        self.assertEqual(snap["last"]["generate"]["duration_sec"], 12)

    def test_non_ok_counts_error(self):
        rt = RuntimeState()
        rt.begin("chat", conversation_id="c-1")
        rt.end("chat", "error", error="连接超时")
        snap = rt.snapshot()
        self.assertEqual(snap["counters"]["chat"], 1)
        self.assertEqual(snap["counters"]["errors"], 1)
        self.assertEqual(snap["last_error"]["message"], "连接超时")

    def test_mark_error_without_task(self):
        rt = RuntimeState()
        rt.mark_error("chat", "Ollama 未运行", where="auto")
        snap = rt.snapshot()
        self.assertEqual(snap["counters"]["errors"], 1)
        self.assertEqual(snap["last_error"]["detail"], {"where": "auto"})

    def test_unknown_kind(self):
        with self.assertRaises(ValueError):
            RuntimeState().begin("unknown")


class Stage7BackupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="wb_backup_")
        for dirname, files in {
            "history": {"convs/01.json": '{"id":1}', "index.json": "{}"},
            "settings": {"app_settings.json": "{}", "app_settings.bak.json": "{}"},
            "workflows": {"a.json": "{}", "mapping.json": "{}"},
            "outputs": {"big.png": "not-included"},
            "logs": {"workbench.log": "not-included"},
        }.items():
            for rel, content in files.items():
                path = os.path.join(self.tmp, dirname, rel)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(content)
        with open(os.path.join(self.tmp, "config.json"), "w", encoding="utf-8") as fh:
            fh.write('{"app": {"version": "2.0"}}')
        self.backups = BackupManager(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_create_and_manifest(self):
        info = self.backups.create(note="阶段 7 单测")
        self.assertTrue(info["ok"])
        self.assertRegex(info["name"], r"^backup-\d{8}-\d{6}(-\d+)?\.zip$")
        self.assertEqual(info["file_count"], 7)
        self.assertEqual(info["counts"]["history"], 2)
        with zipfile.ZipFile(info["path"]) as zf:
            names = zf.namelist()
            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
            self.assertNotIn("outputs/big.png", names)
            self.assertNotIn("logs/workbench.log", names)
            self.assertIn("manifest.json", names)
            self.assertEqual(manifest["version"], "2.0")
            self.assertEqual(manifest["note"], "阶段 7 单测")
            self.assertEqual(len(manifest["files"]), 7)
            for item in manifest["files"]:
                self.assertEqual(len(item["sha256"]), 64)

    def test_list_and_crc(self):
        info = self.backups.create()
        items = self.backups.list()
        self.assertEqual(len(items), 1)
        self.assertTrue(items[0]["ok"])
        self.assertEqual(items[0]["name"], info["name"])
        self.assertEqual(items[0]["counts"]["settings"], 2)
        zip_info = self.backups.info()
        self.assertEqual(zip_info["count"], 1)
        self.assertGreater(zip_info["bytes"], 0)

    def test_delete_moves_to_trash(self):
        info = self.backups.create()
        result = self.backups.delete(info["name"])
        self.assertTrue(result["ok"])
        self.assertFalse(os.path.isfile(info["path"]))
        self.assertTrue(os.path.isfile(os.path.join(self.backups.trash_dir, result["trashed"])))
        self.assertEqual(self.backups.list(), [])

    def test_bad_name(self):
        self.assertIsNone(self.backups.path_for("../evil.zip"))
        self.assertIsNone(self.backups.path_for("backup-x.zip"))
        result = self.backups.delete("../../x.zip")
        self.assertFalse(result["ok"])


class Stage7SettingsTests(unittest.TestCase):
    def test_validate_whitelist_and_clamp(self):
        clean, warnings = validate_patch({
            "application": {"theme": "light", "root": "/etc", "confirm_delete": "false"},
            "chat": {"history_max_messages": 999, "system_prompt_variant": "精简版"},
            "unknown": {"x": 1},
        })
        self.assertEqual(clean["application"]["theme"], "dark")
        self.assertNotIn("root", clean["application"])
        self.assertNotIn("confirm_delete", clean["application"])
        self.assertEqual(clean["chat"]["history_max_messages"], 60)
        self.assertEqual(clean["chat"]["system_prompt_variant"], "精简版")
        self.assertNotIn("unknown", clean)
        self.assertTrue(any("收窄到 60" in w for w in warnings))

    def test_validate_url_and_variant(self):
        clean, warnings = validate_patch({
            "ollama": {"base_url": "ftp://x", "model": "m"},
            "chat": {"system_prompt_variant": "自定义"},
        })
        self.assertNotIn("base_url", clean.get("ollama", {}))
        self.assertEqual(clean["ollama"]["model"], "m")
        self.assertNotIn("system_prompt_variant", clean.get("chat", {}))
        self.assertTrue(warnings)

    def test_store_save_and_warning(self):
        tmp = tempfile.mkdtemp(prefix="wb_settings_")
        try:
            store = SettingsStore(tmp)
            old = store.load()
            self.assertEqual(old["chat"]["history_max_messages"], 20)
            result = store.save({"chat": {"history_max_messages": 2},
                                 "application": {"theme": "dark"}})
            self.assertIsInstance(result, dict)
            self.assertEqual(result["chat"]["history_max_messages"], 2)
            self.assertTrue(os.path.isfile(store.backup_path))
            store.last_warnings = []
            result = store.save({"chat": {"history_max_messages": 61}})
            self.assertEqual(result["chat"]["history_max_messages"], 60)
            self.assertIn("收窄到 60", "；".join(store.last_warnings))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
