# -*- coding: utf-8 -*-
"""阶段 4 测试：工作流解析（按连线判定正负）与工作流库。

运行：python -m unittest discover -s tests -v
"""

import json
import os
import sys
import tempfile
import unittest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from app import comfy_workflow                       # noqa: E402
from app.workflow_lib import WorkflowLibrary         # noqa: E402

REAL_WF = r"D:\AI\Qiuye\ComfyUI-aki-v3.2\ComfyUI\user\default\workflows\suyuexisdxl.json"


def ui_workflow(nodes, links):
    return {"last_node_id": 99, "last_link_id": 99, "nodes": nodes, "links": links,
            "version": 0.4}


def node(nid, ntype, widgets=None, inputs=None, title=""):
    return {"id": nid, "type": ntype, "widgets_values": widgets or [],
            "inputs": inputs or [], "outputs": [], "title": title}


API_WF = {
    "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "intorealismUltra_v80.safetensors"}},
    "2": {"class_type": "CLIPTextEncode", "inputs": {"text": "api positive", "clip": ["1", 1]}},
    "3": {"class_type": "CLIPTextEncode", "inputs": {"text": "api negative", "clip": ["1", 1]}},
    "4": {"class_type": "KSampler", "inputs": {"seed": 777, "steps": 28, "cfg": 6.5,
                                              "sampler_name": "euler", "scheduler": "normal",
                                              "denoise": 1,
                                              "model": ["1", 0], "positive": ["2", 0],
                                              "negative": ["3", 0], "latent_image": ["5", 0]}},
    "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 768, "height": 1024,
                                                      "batch_size": 1}},
}


class RealWorkflowTests(unittest.TestCase):
    """阶段 4 验收：用 IntoRealism Ultra V8 工作流，逐项核对。"""

    def setUp(self):
        self.parsed = comfy_workflow.parse_workflow(REAL_WF)

    def test_checkpoint(self):
        self.assertEqual(self.parsed["checkpoint"]["name"], "intorealismUltra_v80.safetensors")
        self.assertEqual(self.parsed["checkpoint"]["node_id"], "1")

    def test_positive_by_link(self):
        self.assertEqual(self.parsed["positive"]["node_ids"], ["4"])
        self.assertEqual(self.parsed["positive"]["source"], "link")
        self.assertIn("suyuexi, 1girl", self.parsed["positive"]["text"])

    def test_negative_by_link(self):
        self.assertEqual(self.parsed["negative"]["node_ids"], ["5"])
        self.assertIn("lowres", self.parsed["negative"]["text"])

    def test_lora(self):
        lora = self.parsed["loras"][0]
        self.assertEqual(lora["name"], "suyuexifull_c1-st6000.safetensors")
        self.assertEqual(lora["strength_model"], 0.7)
        self.assertEqual(lora["strength_clip"], 0.85)

    def test_resolution_and_sampler(self):
        self.assertEqual((self.parsed["latent"]["width"], self.parsed["latent"]["height"]),
                         (832, 1216))
        s = self.parsed["sampler"]
        self.assertEqual(s["steps"], 35)
        self.assertEqual(s["cfg"], 5.5)
        self.assertEqual(s["sampler_name"], "dpmpp_2m_sde")
        self.assertEqual(s["scheduler"], "karras")
        self.assertEqual(s["seed"], 231661496131269)

    def test_summary_mentions_link_based(self):
        text = comfy_workflow.summarize(self.parsed)
        self.assertIn("按连线判定", text)
        self.assertIn("intorealismUltra_v80.safetensors", text)


class LinkTracingTests(unittest.TestCase):
    def test_titles_and_ids_do_not_decide(self):
        # 节点 4 的标题写 negative，但连的是 positive；节点 5 反之。
        wf = ui_workflow(
            nodes=[
                node(1, "CheckpointLoaderSimple", ["c.safetensors"]),
                node(4, "CLIPTextEncode", ["POS ACTUAL"], title="negative"),
                node(5, "CLIPTextEncode", ["NEG ACTUAL"], title="positive"),
                node(6, "EmptyLatentImage", [832, 1216, 1]),
                node(7, "KSampler", [1, "randomize", 30, 6, "euler", "normal", 1],
                     inputs=[{"name": "positive", "link": 70},
                             {"name": "negative", "link": 80}]),
            ],
            links=[[70, 4, 0, 7, 1, "CONDITIONING"],
                   [80, 5, 0, 7, 2, "CONDITIONING"]])
        parsed = comfy_workflow.parse_workflow(wf)
        self.assertEqual(parsed["positive"]["node_ids"], ["4"])
        self.assertEqual(parsed["positive"]["text"], "POS ACTUAL")
        self.assertEqual(parsed["negative"]["node_ids"], ["5"])
        self.assertEqual(parsed["negative"]["text"], "NEG ACTUAL")

    def test_chain_through_combine_node(self):
        wf = ui_workflow(
            nodes=[
                node(4, "CLIPTextEncode", ["part one"]),
                node(12, "CLIPTextEncode", ["part two"]),
                node(11, "ConditioningCombine",
                     inputs=[{"name": "conditioning_1", "link": 30},
                             {"name": "conditioning_2", "link": 31}]),
                node(7, "KSampler", [1, "randomize", 20, 5, "euler", "normal", 1],
                     inputs=[{"name": "positive", "link": 32}]),
            ],
            links=[[30, 4, 0, 11, 0, "CONDITIONING"],
                   [31, 12, 0, 11, 1, "CONDITIONING"],
                   [32, 11, 0, 7, 1, "CONDITIONING"]])
        parsed = comfy_workflow.parse_workflow(wf)
        self.assertEqual(parsed["positive"]["node_ids"], ["4", "12"])
        self.assertIn("part one", parsed["positive"]["text"])
        self.assertIn("part two", parsed["positive"]["text"])

    def test_api_format_by_reference(self):
        parsed = comfy_workflow.parse_workflow(API_WF)
        self.assertEqual(parsed["format"], "api")
        self.assertEqual(parsed["checkpoint"]["name"], "intorealismUltra_v80.safetensors")
        self.assertEqual(parsed["positive"]["node_ids"], ["2"])
        self.assertEqual(parsed["negative"]["node_ids"], ["3"])
        self.assertEqual(parsed["sampler"]["seed"], 777)
        self.assertEqual(parsed["sampler"]["steps"], 28)
        self.assertEqual((parsed["latent"]["width"], parsed["latent"]["height"]), (768, 1024))

    def test_no_sampler_is_honest(self):
        wf = ui_workflow(
            nodes=[node(1, "CheckpointLoaderSimple", ["c.safetensors"]),
                   node(4, "CLIPTextEncode", ["only text"])],
            links=[])
        parsed = comfy_workflow.parse_workflow(wf)
        self.assertEqual(parsed["positive"]["source"], "unresolved")
        self.assertTrue(any("KSampler" in w for w in parsed["warnings"]))

    def test_manual_mapping_overrides(self):
        parsed = comfy_workflow.parse_workflow(REAL_WF, mapping={"positive_node": "5"})
        self.assertEqual(parsed["positive"]["node_ids"], ["5"])
        self.assertEqual(parsed["positive"]["source"], "manual")
        self.assertIn("lowres", parsed["positive"]["text"])
        # 负向没被覆盖，仍是连线判定
        self.assertEqual(parsed["negative"]["source"], "link")

    def test_mapping_to_missing_node_warns(self):
        parsed = comfy_workflow.parse_workflow(REAL_WF, mapping={"negative_node": "99"})
        self.assertEqual(parsed["negative"]["source"], "link")
        self.assertTrue(any("99" in w for w in parsed["warnings"]))


class WorkflowLibTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="pw_wf_")
        self.comfy = os.path.join(self.tmp, "comfy")
        os.makedirs(self.comfy, exist_ok=True)
        with open(os.path.join(self.comfy, "existing.json"), "w", encoding="utf-8") as fh:
            json.dump(API_WF, fh)
        self.lib = WorkflowLibrary(self.tmp, self.comfy)

    def test_import_ui_workflow(self):
        text = json.dumps(ui_workflow(
            nodes=[node(1, "CheckpointLoaderSimple", ["c.safetensors"]),
                   node(4, "CLIPTextEncode", ["hello"]),
                   node(7, "KSampler", [1, "randomize", 30, 6, "euler", "normal", 1],
                        inputs=[{"name": "positive", "link": 70}])],
            links=[[70, 4, 0, 7, 1, "CONDITIONING"]]), ensure_ascii=False)
        res = self.lib.import_text("my_flow.json", text)
        self.assertTrue(res["ok"], res)
        self.assertEqual(res["entry"]["name"], "my_flow.json")
        self.assertEqual(res["entry"]["format"], "ui")
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "workflows", "my_flow.json")))
        self.assertEqual(res["parsed"]["positive"]["node_ids"], ["4"])

    def test_import_api_workflow_and_duplicate_name(self):
        text = json.dumps(API_WF)
        first = self.lib.import_text("api_flow.json", text)
        self.assertTrue(first["ok"])
        second = self.lib.import_text("api_flow.json", text)
        self.assertTrue(second["ok"])
        self.assertEqual(second["entry"]["name"], "api_flow-2.json")

    def test_import_rejects_bad_json(self):
        res = self.lib.import_text("bad.json", "{ not json")
        self.assertFalse(res["ok"])
        res2 = self.lib.import_text("bad.json", json.dumps({"foo": 1}))
        self.assertFalse(res2["ok"])

    def test_path_traversal_blocked(self):
        self.assertEqual(self.lib.resolve("../config.json"), (None, None))
        self.assertEqual(self.lib.safe_name("..\\..\\config.json"), "config.json")
        self.assertIsNone(self.lib.save_mapping("../x", {"positive_node": "1"}))

    def test_mapping_roundtrip_and_applied(self):
        self.lib.import_text("api_flow.json", json.dumps(API_WF))
        saved = self.lib.save_mapping("api_flow.json", {"positive_node": "3", "negative_node": "2"})
        self.assertEqual(saved["positive_node"], "3")
        self.assertEqual(self.lib.load_mapping("api_flow.json")["negative_node"], "2")
        items = {x["name"]: x for x in self.lib.list_all()}
        self.assertTrue(items["api_flow.json"]["has_mapping"])
        self.assertEqual(items["api_flow.json"]["positive_nodes"], ["3"])

    def test_list_merges_sources(self):
        self.lib.import_text("api_flow.json", json.dumps(API_WF))
        items = {x["name"]: x for x in self.lib.list_all()}
        self.assertEqual(items["existing.json"]["source"], "comfyui")
        self.assertEqual(items["api_flow.json"]["source"], "workbench")
        # workflows_index.json 是工作台内部索引，不是工作流，不能出现在列表
        self.assertNotIn("workflows_index.json", items)
        self.assertTrue(os.path.isfile(self.lib.index_path))
        self.assertEqual(self.lib.resolve("workflows_index.json"), (None, None))
        self.assertFalse(self.lib.delete("workflows_index.json"))
        self.assertTrue(os.path.isfile(self.lib.index_path))

    def test_delete_only_imported(self):
        self.lib.import_text("api_flow.json", json.dumps(API_WF))
        self.assertTrue(self.lib.delete("api_flow.json"))
        self.assertFalse(os.path.isfile(os.path.join(self.tmp, "workflows", "api_flow.json")))
        self.assertTrue(any("api_flow" in fn for fn in
                            os.listdir(os.path.join(self.tmp, "workflows", "_archive"))))
        self.assertFalse(self.lib.delete("existing.json"))
        self.assertTrue(os.path.isfile(os.path.join(self.comfy, "existing.json")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
