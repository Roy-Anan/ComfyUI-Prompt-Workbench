# -*- coding: utf-8 -*-
"""阶段 3 验收测试：对话持久化 / 提示词记录 / 设置 / 重启后仍在。

运行：python -m unittest discover -s tests -v
"""

import json
import os
import sys
import tempfile
import time
import unittest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from app import prompt_extract                      # noqa: E402
from app.history_store import HistoryStore          # noqa: E402
from app.settings_store import SettingsStore        # noqa: E402

SAMPLE_REPLY = """【当前模型】intorealismUltra_v80.safetensors
【架构 / 派系 / 画风】SDXL / 写实 XL / 写实人像

【Positive Prompt】
```
a white-haired girl sitting by the window, afternoon backlight, soft shadows
```

【Negative Prompt】
```
lowres, bad anatomy, watermark
```

【Generation Settings】
Resolution=832x1216; Steps=[作者推荐] 6~12

【模型适配说明】
早期蒸馏版，低步低 CFG。

【待确认项】无
"""


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="pw_hist_")
        self.store = HistoryStore(self.tmp)

    def test_create_writes_file_with_required_fields(self):
        conv = self.store.create(title="测试", checkpoint="intorealismUltra_v80.safetensors",
                                 profile_name="IntoRealism_Ultra_V8.txt",
                                 workflow_id="suyuexisdxl.json")
        self.assertTrue(conv["conversation_id"].startswith("c-"))
        path = os.path.join(self.tmp, "history", "conversations",
                            conv["conversation_id"] + ".json")
        self.assertTrue(os.path.isfile(path))
        with open(path, encoding="utf-8-sig") as fh:
            disk = json.load(fh)
        for key in ("conversation_id", "title", "created_at", "updated_at",
                    "messages", "checkpoint", "profile_name", "workflow_id"):
            self.assertIn(key, disk)
        self.assertEqual(disk["checkpoint"], "intorealismUltra_v80.safetensors")

    def test_append_then_reload_from_disk(self):
        conv = self.store.create()
        cid = conv["conversation_id"]
        self.store.append_message(cid, "user", "白发少女窗边逆光")
        self.store.append_message(cid, "assistant", "【Positive Prompt】...", meta={"attempts": 1})

        fresh = HistoryStore(self.tmp)          # 模拟重启：新的实例
        loaded = fresh.load(cid)
        self.assertEqual(len(loaded["messages"]), 2)
        self.assertEqual(loaded["messages"][0]["role"], "user")
        self.assertEqual(loaded["messages"][1]["meta"]["attempts"], 1)
        self.assertEqual(loaded["messages"][1]["seq"], 2)
        self.assertTrue(loaded["updated_at"] >= loaded["created_at"])

    def test_title_auto_from_first_user_message(self):
        conv = self.store.create()
        cid = conv["conversation_id"]
        self.store.append_message(cid, "user", "窗边白发少女，午后逆光\n第二行不该进标题")
        self.assertEqual(self.store.load(cid)["title"], "窗边白发少女，午后逆光")

    def test_rename(self):
        cid = self.store.create()["conversation_id"]
        renamed = self.store.rename(cid, "  新标题  ")
        self.assertEqual(renamed["title"], "新标题")
        self.assertEqual(self.store.load(cid)["title"], "新标题")

    def test_list_sorted_by_updated(self):
        a = self.store.create(title="A")["conversation_id"]
        b = self.store.create(title="B")["conversation_id"]
        time.sleep(0.02)          # 时间戳是毫秒级，留一点间隔避免同毫秒
        self.store.append_message(a, "user", "让 A 变成最近更新")
        items = self.store.list_conversations()
        self.assertEqual(items[0]["conversation_id"], a)
        self.assertEqual(items[1]["conversation_id"], b)

    def test_archive_moves_file_and_disappears_from_list(self):
        cid = self.store.create()["conversation_id"]
        self.assertTrue(self.store.archive(cid))
        self.assertIsNone(self.store.load(cid))
        self.assertFalse(any(c["conversation_id"] == cid for c in self.store.list_conversations()))
        archive_dir = os.path.join(self.tmp, "history", "conversations", "_archive")
        self.assertTrue(any(cid in fn for fn in os.listdir(archive_dir)))

    def test_reject_bad_conversation_id(self):
        for bad in ("../config", "c-20260101-000000-zzzz", "", None, "config"):
            self.assertIsNone(self.store.load(bad))
            self.assertFalse(self.store.archive(bad))

    def test_history_for_ollama_window(self):
        cid = self.store.create()["conversation_id"]
        for i in range(8):
            self.store.append_message(cid, "user" if i % 2 == 0 else "assistant", "m%d" % i)
        window = self.store.history_for_ollama(cid, limit=4)
        self.assertEqual(len(window), 4)
        self.assertEqual(window[-1]["content"], "m7")
        self.assertEqual(self.store.history_for_ollama(cid, limit=4, exclude_last=True)[-1]["content"], "m6")

    def test_export_markdown(self):
        cid = self.store.create(title="导出测试")["conversation_id"]
        self.store.append_message(cid, "user", "需求")
        self.store.append_message(cid, "assistant", "【Positive Prompt】abc")
        md = self.store.export_markdown(cid)
        self.assertIn("# 导出测试", md)
        self.assertIn("## 我", md)
        self.assertIn("## 提示词助手", md)
        self.assertIn("abc", md)

    def test_index_rebuilt_with_counts(self):
        cid = self.store.create()["conversation_id"]
        self.store.append_message(cid, "user", "一")
        self.store.save_prompt(cid, "pos", "neg", "settings")
        index = self.store.rebuild_index()
        conv_entry = index["conversations"][0]
        self.assertEqual(conv_entry["message_count"], 1)
        self.assertEqual(conv_entry["prompt_count"], 1)
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "history", "history_index.json")))


class PromptExtractTests(unittest.TestCase):
    def test_extract_positive_negative_strips_fences(self):
        parts = prompt_extract.extract(SAMPLE_REPLY)
        self.assertEqual(parts["positive"],
                         "a white-haired girl sitting by the window, afternoon backlight, soft shadows")
        self.assertEqual(parts["negative"], "lowres, bad anatomy, watermark")
        self.assertIn("832x1216", parts["settings"])
        self.assertIn("蒸馏版", parts["adapt"])

    def test_extract_english_headings(self):
        text = "【Current Model】x\n\n【Positive Prompt】a cat\n\n【Negative Prompt】blurry"
        parts = prompt_extract.extract(text)
        self.assertEqual(parts["positive"], "a cat")
        self.assertEqual(parts["negative"], "blurry")

    def test_save_prompt_links_conversation(self):
        tmp = tempfile.mkdtemp(prefix="pw_prompt_")
        store = HistoryStore(tmp)
        cid = store.create(checkpoint="intorealismUltra_v80.safetensors",
                           profile_name="IntoRealism_Ultra_V8.txt")["conversation_id"]
        rec = store.save_prompt(cid, "pos text", "neg text", "steps 10",
                               checkpoint="intorealismUltra_v80.safetensors",
                               profile="IntoRealism_Ultra_V8.txt")
        self.assertTrue(rec["prompt_id"].startswith("p-"))
        self.assertEqual(rec["positive"], "pos text")
        self.assertEqual(store.load(cid)["prompt_ids"], [rec["prompt_id"]])
        listed = store.list_prompts(cid)
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["profile"], "IntoRealism_Ultra_V8.txt")


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="pw_set_")
        self.store = SettingsStore(self.tmp)

    def test_defaults_written_on_first_load(self):
        data = self.store.load()
        self.assertTrue(data["application"]["auto_save_history"])
        self.assertEqual(data["chat"]["history_max_messages"], 20)
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "settings", "app_settings.json")))

    def test_save_backs_up_previous(self):
        self.store.load()
        self.store.save({"chat": {"history_max_messages": 10}})
        backup = os.path.join(self.tmp, "settings", "app_settings.bak.json")
        self.assertTrue(os.path.isfile(backup))
        self.assertEqual(self.store.load()["chat"]["history_max_messages"], 10)

    def test_unknown_keys_ignored(self):
        self.store.save({"weird": {"x": 1}, "chat": {"nope": 5}})
        data = self.store.load()
        self.assertNotIn("weird", data)
        self.assertNotIn("nope", data["chat"])

    def test_corrupt_file_recovered(self):
        path = os.path.join(self.tmp, "settings", "app_settings.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("{ broken json")
        data = self.store.load()
        self.assertTrue(data["application"]["auto_save_history"])
        self.assertTrue(any(fn.startswith("app_settings.json.corrupt-")
                            for fn in os.listdir(os.path.dirname(path))))


if __name__ == "__main__":
    unittest.main(verbosity=2)
