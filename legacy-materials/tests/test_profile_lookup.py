# -*- coding: utf-8 -*-
"""阶段 1 验收测试：规则包整合完整性 + Profile 精确匹配。

运行：python -m unittest discover -s tests -v
"""

import hashlib
import json
import os
import sys
import unittest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from app.profile_lookup import ProfileLookup  # noqa: E402

CONFIG_PATH = os.path.join(BASE, "config.json")
SOURCE_PROFILES = os.path.join(BASE, "rules_source", "ComfyUI_Prompt_Master_V1", "MODEL_PROFILES")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def checkpoints_dir():
    try:
        with open(CONFIG_PATH, encoding="utf-8-sig") as fh:
            cfg = json.load(fh)
        path = (cfg.get("comfyui") or {}).get("models_dir")
        return path if path and os.path.isdir(path) else None
    except Exception:
        return None


class ProfileLookupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lk = ProfileLookup()
        cls.models = cls.lk.list_models()

    # -------------------------------------------------- 规则包整合（验收项 1～4）
    def test_01_database_has_13_entries(self):
        self.assertEqual(len(self.models), 13, "模型数据库应登记 13 个 checkpoint")
        self.assertEqual(self.lk.problems, [], "模型数据库解析问题：%s" % self.lk.problems)

    def test_02_all_registered_models_exact_match(self):
        for m in self.models:
            with self.subTest(checkpoint=m["checkpoint"]):
                result = self.lk.lookup(m["checkpoint"])
                self.assertTrue(result["ok"], result.get("message"))
                self.assertEqual(result["match_type"], "exact")
                self.assertEqual(result["registered_name"], m["checkpoint"])
                self.assertTrue(os.path.isfile(result["profile_path"]))
                self.assertTrue(self.lk.profile_text(m["checkpoint"]).strip())

    def test_03_intorealism_maps_to_v8_profile(self):
        result = self.lk.lookup("intorealismUltra_v80.safetensors")
        self.assertTrue(result["ok"])
        self.assertEqual(result["profile_file"], "IntoRealism_Ultra_V8.txt")

    def test_04_unknown_checkpoint_is_unregistered(self):
        result = self.lk.lookup("unknown_checkpoint.safetensors")
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "unregistered")
        self.assertIn("未登记", result["message"])

    # -------------------------------------------------- 不模糊匹配（验收项 4）
    def test_05_keywords_are_not_fuzzy_matched(self):
        for keyword in ["Huslyo", "anything", "Juggernaut", "pony", "suyuexi", "", "  "]:
            with self.subTest(input=keyword):
                self.assertFalse(self.lk.lookup(keyword)["ok"],
                                 "关键词 %r 不应被匹配到任何 profile" % keyword)

    def test_06_same_series_versions_not_cross_matched(self):
        # Profile 文件名、系列名、其他版本名都不是 checkpoint 文件名，必须一律未登记
        cases = [
            "HuslyoRealismXL_V2_DMD.safetensors",
            "HuslyoRealismXL_V3.safetensors",
            "Juggernaut_XI.safetensors",
            "JuggernautXL_Ragnarok.safetensors",
            "ponyDiffusionV6XL_v7.safetensors",
            "IntoRealism_Ultra_V8.txt",
        ]
        for name in cases:
            with self.subTest(checkpoint=name):
                result = self.lk.lookup(name)
                self.assertFalse(result["ok"], "%s 不是登记名，不能串版本" % name)
                self.assertEqual(result["reason"], "unregistered")

    # -------------------------------------------------- 匹配细节
    def test_07_subdirectory_prefix_is_stripped(self):
        result = self.lk.lookup("SDXL/intorealismUltra_v80.safetensors")
        self.assertTrue(result["ok"])
        self.assertEqual(result["checkpoint"], "intorealismUltra_v80.safetensors")

    def test_08_case_difference_is_flagged_not_silent(self):
        result = self.lk.lookup("INTOREALISMULTRA_V80.SAFETENSORS")
        self.assertTrue(result["ok"])
        self.assertEqual(result["match_type"], "case-insensitive")
        self.assertTrue(result["warnings"])

    # -------------------------------------------------- 原始文件一致性
    def test_09_profiles_identical_to_source_package(self):
        for name in sorted(os.listdir(os.path.join(BASE, "profiles"))):
            if not name.lower().endswith(".txt"):
                continue
            with self.subTest(profile=name):
                mine = os.path.join(BASE, "profiles", name)
                original = os.path.join(SOURCE_PROFILES, name)
                self.assertTrue(os.path.isfile(original), "原始规则包缺少 %s" % name)
                self.assertEqual(sha256(mine), sha256(original),
                                 "profiles/%s 与原始规则包不一致" % name)

    def test_10_integrity_clean(self):
        report = self.lk.integrity(checkpoints_dir=checkpoints_dir())
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["db_entries"], 13)
        self.assertEqual(report["profile_files"], 13)
        self.assertEqual(report["index_entries"], 13)
        self.assertFalse(report["missing_profiles"])
        self.assertFalse(report["orphan_profiles"])

    def test_11_checkpoint_files_on_disk(self):
        directory = checkpoints_dir()
        if not directory:
            self.skipTest("config.json 未配置有效的 comfyui.models_dir")
        missing = self.lk.integrity(checkpoints_dir=directory)["missing_checkpoints"]
        self.assertFalse(missing, "磁盘上缺少 checkpoint 文件：%s" % missing)


if __name__ == "__main__":
    unittest.main(verbosity=2)
