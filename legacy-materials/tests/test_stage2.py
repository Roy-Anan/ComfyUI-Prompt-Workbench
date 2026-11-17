# -*- coding: utf-8 -*-
"""阶段 2 验收测试：工作流读取 + Profile 自动注入 + LoRA 架构核对。

运行：python -m unittest tests.test_stage2 -v
"""

import json
import os
import sys
import unittest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from app import comfy_workflow, lora_meta                      # noqa: E402
from app.profile_lookup import ProfileLookup                   # noqa: E402
from app.prompt_context import ContextBuilder                  # noqa: E402

with open(os.path.join(BASE, "config.json"), encoding="utf-8-sig") as fh:
    CFG = json.load(fh)

COMFY = CFG.get("comfyui", {})
LORAS_DIR = COMFY.get("loras_dir", "")
WF_DIR = COMFY.get("workflows_dir", "")
REAL_WF = os.path.join(WF_DIR, "suyuexisdxl.json")

LOOKUP = ProfileLookup()
BUILDER = ContextBuilder(BASE, LOOKUP, loras_dir=LORAS_DIR,
                         system_variant=CFG.get("workbench", {}).get("system_prompt_variant", "精简版"))


class WorkflowParseTests(unittest.TestCase):
    def test_real_workflow_fields(self):
        if not os.path.isfile(REAL_WF):
            self.skipTest("测试工作流不存在：%s" % REAL_WF)
        parsed = comfy_workflow.parse_workflow(REAL_WF)
        self.assertEqual(parsed["format"], "ui")
        self.assertEqual(parsed["checkpoint"]["name"], "intorealismUltra_v80.safetensors")
        # 阶段 4 起节点 ID 统一按字符串返回（UI / API 两种格式一致）
        self.assertEqual(parsed["checkpoint"]["node_id"], "1")

        self.assertEqual(len(parsed["loras"]), 1)
        lora = parsed["loras"][0]
        self.assertEqual(lora["name"], "suyuexifull_c1-st6000.safetensors")
        self.assertEqual(lora["strength_model"], 0.7)
        self.assertEqual(lora["strength_clip"], 0.85)

        sampler = parsed["sampler"]
        self.assertEqual(sampler["steps"], 35)
        self.assertEqual(sampler["cfg"], 5.5)
        self.assertEqual(sampler["sampler_name"], "dpmpp_2m_sde")
        self.assertEqual(sampler["scheduler"], "karras")
        self.assertEqual(sampler["seed"], 231661496131269)

        self.assertEqual(parsed["latent"]["width"], 832)
        self.assertEqual(parsed["latent"]["height"], 1216)
        self.assertEqual(len(parsed["text_nodes"]), 2)

    def test_api_format_parsed(self):
        api = {
            "1": {"class_type": "CheckpointLoaderSimple",
                  "inputs": {"ckpt_name": "intorealismUltra_v80.safetensors"}},
            "10": {"class_type": "LoraLoader",
                   "inputs": {"lora_name": "suyuexifull_c1-st6000.safetensors",
                              "strength_model": 0.7, "strength_clip": 0.85}},
            "7": {"class_type": "KSampler",
                  "inputs": {"seed": 123, "steps": 30, "cfg": 6.0,
                             "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0}},
            "6": {"class_type": "EmptyLatentImage",
                  "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
        }
        parsed = comfy_workflow.parse_workflow(api)
        self.assertEqual(parsed["format"], "api")
        self.assertEqual(parsed["checkpoint"]["name"], "intorealismUltra_v80.safetensors")
        self.assertEqual(parsed["loras"][0]["name"], "suyuexifull_c1-st6000.safetensors")
        self.assertEqual(parsed["sampler"]["steps"], 30)
        self.assertEqual(parsed["latent"]["width"], 1024)


class InjectionTests(unittest.TestCase):
    def test_all_13_models_inject_their_own_profile(self):
        """验收要求：13 个模型分别测试，不能只测一个。"""
        models = LOOKUP.list_models()
        self.assertEqual(len(models), 13)
        for item in models:
            with self.subTest(checkpoint=item["checkpoint"]):
                result = BUILDER.build(item["checkpoint"])
                self.assertTrue(result["ok"], result.get("message"))
                meta = result["meta"]
                self.assertEqual(meta["profile_file"], item["profile_file"])
                self.assertIn("【当前模型】%s" % item["checkpoint"], result["system"])

                profile_text = LOOKUP.profile_text(item["checkpoint"]).strip()
                self.assertIn(profile_text[:40], result["system"],
                              "profile 原文没有完整进入 system")
                self.assertEqual(meta["profile_chars"], len(LOOKUP.profile_text(item["checkpoint"])),
                                 "profile 字符数被截断或被改写")

    def test_unregistered_model_rejected(self):
        result = BUILDER.build("unknown_checkpoint.safetensors")
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "unregistered")
        self.assertNotIn("system", result)

    def test_fuzzy_name_rejected(self):
        for bad in ["Huslyo", "anything-v5", "intorealismUltra"]:
            with self.subTest(name=bad):
                self.assertFalse(BUILDER.build(bad)["ok"])

    def test_workflow_context_injected(self):
        if not os.path.isfile(REAL_WF):
            self.skipTest("测试工作流不存在")
        result = BUILDER.build("intorealismUltra_v80.safetensors", REAL_WF)
        self.assertTrue(result["ok"])
        system = result["system"]
        self.assertIn("【当前工作流上下文】", system)
        self.assertIn("suyuexifull_c1-st6000.safetensors", system)
        self.assertIn("35", system)
        self.assertEqual(result["meta"]["workflow"]["name"], "suyuexisdxl.json")
        self.assertEqual(result["meta"]["workflow"]["lora_count"], 1)

    def test_system_prompt_variant_switch(self):
        result = BUILDER.build("intorealismUltra_v80.safetensors", system_variant="全量版")
        self.assertTrue(result["ok"])
        self.assertEqual(result["meta"]["system_prompt_file"], "系统提示词_全量版.txt")

    def test_injection_is_system_plus_model_plus_profile(self):
        result = BUILDER.build("anything-v5.safetensors")
        system = result["system"]
        # 顺序应符合计划书 §6.3：系统提示词 → 当前模型 → profile → 上下文
        idx_system = system.find("## 1. 角色")
        idx_model = system.find("【当前模型】")
        idx_profile = system.find("【当前模型 Profile（原文，未改写）】")
        self.assertGreater(idx_system, -1)
        self.assertGreater(idx_model, idx_system)
        self.assertGreater(idx_profile, idx_model)


class LoraTests(unittest.TestCase):
    def test_sdxl_lora_detected_by_weights(self):
        info = lora_meta.detect_arch("suyuexifull_c1-st6000.safetensors", LORAS_DIR)
        self.assertTrue(info["found"], info.get("error"))
        self.assertEqual(info["arch"], "SDXL")
        self.assertIn("2048", info["evidence"])

    def test_sd15_lora_detected_by_weights(self):
        info = lora_meta.detect_arch("suyuexi.safetensors", LORAS_DIR)
        self.assertTrue(info["found"], info.get("error"))
        self.assertEqual(info["arch"], "SD1.5")
        self.assertIn("768", info["evidence"])

    def test_compatibility_matrix(self):
        self.assertFalse(lora_meta.compatibility("SD1.5", "SDXL")["compatible"])
        self.assertFalse(lora_meta.compatibility("SDXL", "SD1.5")["compatible"])
        self.assertTrue(lora_meta.compatibility("SDXL", "SDXL")["compatible"])
        self.assertTrue(lora_meta.compatibility("SD1.5", "SD1.5")["compatible"])
        self.assertIsNone(lora_meta.compatibility("SDXL", "unknown")["compatible"])

    def test_context_flags_incompatible_lora(self):
        workflow = {
            "nodes": [
                {"id": 1, "type": "CheckpointLoaderSimple",
                 "widgets_values": ["intorealismUltra_v80.safetensors"]},
                {"id": 10, "type": "LoraLoader",
                 "widgets_values": ["suyuexi.safetensors", 0.8, 0.8]},
            ]
        }
        result = BUILDER.build("intorealismUltra_v80.safetensors", workflow)
        self.assertTrue(result["ok"])
        checks = result["meta"]["lora_checks"]
        self.assertEqual(len(checks), 1)
        self.assertEqual(checks[0]["state"], "incompatible")
        self.assertIn("不兼容", result["system"])

    def test_context_accepts_compatible_lora(self):
        workflow = {
            "nodes": [
                {"id": 1, "type": "CheckpointLoaderSimple",
                 "widgets_values": ["intorealismUltra_v80.safetensors"]},
                {"id": 10, "type": "LoraLoader",
                 "widgets_values": ["suyuexifull_c1-st6000.safetensors", 0.7, 0.85]},
            ]
        }
        result = BUILDER.build("intorealismUltra_v80.safetensors", workflow)
        self.assertTrue(result["ok"])
        self.assertEqual(result["meta"]["lora_checks"][0]["state"], "ok")
        self.assertEqual(result["meta"]["lora_checks"][0]["lora_arch"], "SDXL")


if __name__ == "__main__":
    unittest.main(verbosity=2)
