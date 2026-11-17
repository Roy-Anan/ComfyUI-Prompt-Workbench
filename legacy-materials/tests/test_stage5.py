# -*- coding: utf-8 -*-
"""阶段 5 测试：UI → API 转换、提交/轮询客户端、出图记录落盘、图片结构。

不连真 ComfyUI（真出图放在 tests/smoke_server.py 里跑）。
运行：python -m unittest discover -s tests -v
"""

import json
import os
import sys
import tempfile
import time
import unittest
import urllib.error
from unittest import mock

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from app import comfy_api, history_store, server  # noqa: E402


# ---------------------------------------------------------------- 节点定义样例
def spec(order, required, optional=None):
    return {"input": {"required": required, "optional": optional or {}},
            "input_order": {"required": order,
                            "optional": list((optional or {}).keys())}}


INFO = {
    "CheckpointLoaderSimple": spec(["ckpt_name"], {"ckpt_name": [["a.safetensors"], {}]}),
    "CLIPTextEncode": spec(["text", "clip"], {
        "text": ["STRING", {"multiline": True}],
        "clip": ["CLIP", {}]}),
    "LoraLoader": spec(["model", "clip", "lora_name", "strength_model", "strength_clip"], {
        "model": ["MODEL", {}], "clip": ["CLIP", {}],
        "lora_name": [["lora.safetensors"], {}],
        "strength_model": ["FLOAT", {"default": 1.0}],
        "strength_clip": ["FLOAT", {"default": 1.0}]}),
    "EmptyLatentImage": spec(["width", "height", "batch_size"], {
        "width": ["INT", {"default": 512}], "height": ["INT", {"default": 512}],
        "batch_size": ["INT", {"default": 1}]}),
    "KSampler": spec(
        ["model", "seed", "steps", "cfg", "sampler_name", "scheduler",
         "positive", "negative", "latent_image", "denoise"], {
            "model": ["MODEL", {}],
            "seed": ["INT", {"default": 0, "control_after_generate": True}],
            "steps": ["INT", {"default": 20}],
            "cfg": ["FLOAT", {"default": 8.0}],
            "sampler_name": [["euler", "dpmpp_2m_sde"], {}],
            "scheduler": [["normal", "karras"], {}],
            "positive": ["CONDITIONING", {}],
            "negative": ["CONDITIONING", {}],
            "latent_image": ["LATENT", {}],
            "denoise": ["FLOAT", {"default": 1.0}]}),
    "VAEDecode": spec(["samples", "vae"], {"samples": ["LATENT", {}], "vae": ["VAE", {}]}),
    "SaveImage": spec(["images", "filename_prefix"], {
        "images": ["IMAGE", {}],
        "filename_prefix": ["STRING", {"default": "ComfyUI"}]}),
    "Note": spec([], {}),
}


def node(nid, ntype, widgets=None, inputs=None, mode=0, title=""):
    return {"id": nid, "type": ntype, "widgets_values": widgets or [],
            "inputs": inputs or [], "outputs": [], "mode": mode, "title": title}


def ui_workflow(nodes, links):
    return {"last_node_id": 99, "last_link_id": 99, "nodes": nodes, "links": links,
            "version": 0.4}


def base_workflow():
    """1 模型 → 10 LoRA → 7 采样；4/5 文本；6 空 latent；8 解码；9 保存。"""
    nodes = [
        node(1, "CheckpointLoaderSimple", ["a.safetensors"]),
        node(4, "CLIPTextEncode", ["hello"], [{"name": "clip", "link": 12}]),
        node(5, "CLIPTextEncode", ["bad"], [{"name": "clip", "link": 12}]),
        node(6, "EmptyLatentImage", [832, 1216, 1]),
        node(7, "KSampler", [1234, "randomize", 35, 5.5, "dpmpp_2m_sde", "karras", 1], [
            {"name": "model", "link": 71}, {"name": "positive", "link": 41},
            {"name": "negative", "link": 51}, {"name": "latent_image", "link": 61}]),
        node(8, "VAEDecode", None, [{"name": "samples", "link": 81},
                                    {"name": "vae", "link": 13}]),
        node(9, "SaveImage", ["pony"], [{"name": "images", "link": 91}]),
        node(10, "LoraLoader", ["lora.safetensors", 0.7, 0.85],
             [{"name": "model", "link": 11}, {"name": "clip", "link": 12}]),
    ]
    links = [
        [11, 1, 0, 10, 0, "MODEL"], [12, 1, 1, 4, 1, "CLIP"],
        [71, 10, 0, 7, 0, "MODEL"], [41, 4, 0, 7, 1, "CONDITIONING"],
        [51, 5, 0, 7, 2, "CONDITIONING"], [61, 6, 0, 7, 3, "LATENT"],
        [81, 7, 0, 8, 0, "LATENT"], [82, 1, 2, 8, 1, "VAE"], [91, 8, 0, 9, 0, "IMAGE"],
        [13, 1, 2, 8, 1, "VAE"],
    ]
    return ui_workflow(nodes, links)


class ConversionTests(unittest.TestCase):
    def setUp(self):
        self.prompt, self.warnings = comfy_api.convert_ui_to_api(base_workflow(), INFO)

    def test_nodes_keep_ids(self):
        self.assertEqual(sorted(self.prompt, key=int),
                         ["1", "4", "5", "6", "7", "8", "9", "10"])
        self.assertEqual(self.prompt["7"]["class_type"], "KSampler")

    def test_widgets_in_order(self):
        self.assertEqual(self.prompt["6"]["inputs"], {"width": 832, "height": 1216,
                                                     "batch_size": 1})
        self.assertEqual(self.prompt["1"]["inputs"]["ckpt_name"], "a.safetensors")
        self.assertEqual(self.prompt["4"]["inputs"]["text"], "hello")
        self.assertEqual(self.prompt["9"]["inputs"]["filename_prefix"], "pony")

    def test_control_after_generate_skipped(self):
        sampler = self.prompt["7"]["inputs"]
        self.assertEqual(sampler["seed"], 1234)
        self.assertEqual(sampler["steps"], 35)      # 没有把 "randomize" 当成步数
        self.assertEqual(sampler["cfg"], 5.5)
        self.assertEqual(sampler["sampler_name"], "dpmpp_2m_sde")
        self.assertEqual(sampler["scheduler"], "karras")
        self.assertEqual(sampler["denoise"], 1)

    def test_links_become_pairs(self):
        sampler = self.prompt["7"]["inputs"]
        self.assertEqual(sampler["model"], ["10", 0])
        self.assertEqual(sampler["positive"], ["4", 0])
        self.assertEqual(sampler["negative"], ["5", 0])
        self.assertEqual(sampler["latent_image"], ["6", 0])
        self.assertEqual(self.prompt["10"]["inputs"]["strength_model"], 0.7)
        self.assertEqual(self.prompt["10"]["inputs"]["strength_clip"], 0.85)
        self.assertEqual(self.prompt["9"]["inputs"]["images"], ["8", 0])

    def test_no_warnings_on_clean_graph(self):
        self.assertEqual(self.warnings, [])

    def test_reroute_is_traced(self):
        wf = base_workflow()
        wf["nodes"].append(node(20, "Reroute", None, [{"name": "", "link": 42}]))
        wf["links"].append([42, 4, 0, 20, 0, "CONDITIONING"])
        wf["links"].append([43, 20, 0, 7, 1, "CONDITIONING"])
        for item in wf["nodes"]:
            if item["id"] == 7:
                item["inputs"][1]["link"] = 43
        prompt, _ = comfy_api.convert_ui_to_api(wf, {**INFO, "Reroute": spec([], {})})
        self.assertEqual(prompt["7"]["inputs"]["positive"], ["4", 0])

    def test_primitive_node_value(self):
        wf = base_workflow()
        wf["nodes"].append(node(30, "PrimitiveNode", ["来自 Primitive"]))
        wf["links"].append([44, 30, 0, 4, 0, "STRING"])
        for item in wf["nodes"]:
            if item["id"] == 4:
                item["inputs"].append({"name": "text", "link": 44})
        prompt, _ = comfy_api.convert_ui_to_api(wf, {**INFO, "PrimitiveNode": spec([], {})})
        self.assertEqual(prompt["4"]["inputs"]["text"], "来自 Primitive")

    def test_widget_dict_values(self):
        wf = base_workflow()
        for item in wf["nodes"]:
            if item["id"] == 4:
                item["widgets_values"] = {"text": "dict 里的文本"}
        prompt, _ = comfy_api.convert_ui_to_api(wf, INFO)
        self.assertEqual(prompt["4"]["inputs"]["text"], "dict 里的文本")

    def test_muted_node_skipped(self):
        wf = base_workflow()
        for item in wf["nodes"]:
            if item["id"] == 10:
                item["mode"] = 2
        prompt, warnings = comfy_api.convert_ui_to_api(wf, INFO)
        self.assertNotIn("10", prompt)
        self.assertTrue(any("静音" in w for w in warnings))

    def test_unknown_node_raises(self):
        wf = base_workflow()
        wf["nodes"].append(node(40, "SomeCustomNode", ["x"]))
        with self.assertRaises(comfy_api.ConversionError):
            comfy_api.convert_ui_to_api(wf, INFO)

    def test_not_ui_workflow_raises(self):
        with self.assertRaises(comfy_api.ConversionError):
            comfy_api.convert_ui_to_api({"1": {"class_type": "X", "inputs": {}}}, INFO)

    def test_missing_link_raises(self):
        wf = base_workflow()
        wf["links"] = [l for l in wf["links"] if l[0] != 41]
        with self.assertRaises(comfy_api.ConversionError):
            comfy_api.convert_ui_to_api(wf, INFO)


class TextAndOverrideTests(unittest.TestCase):
    def setUp(self):
        self.prompt, _ = comfy_api.convert_ui_to_api(base_workflow(), INFO)

    def test_set_text_inputs(self):
        changed = comfy_api.set_text_inputs(self.prompt, ["4", "5"], "新提示词")
        self.assertEqual(changed, ["4", "5"])
        self.assertEqual(self.prompt["4"]["inputs"]["text"], "新提示词")
        self.assertEqual(self.prompt["5"]["inputs"]["text"], "新提示词")
        self.assertEqual(self.prompt["7"]["inputs"]["steps"], 35)

    def test_set_text_inputs_unknown_node(self):
        self.assertEqual(comfy_api.set_text_inputs(self.prompt, ["999"], "x"), [])

    def test_apply_overrides(self):
        applied = comfy_api.apply_overrides(self.prompt, ["7"],
                                            {"seed": 9, "steps": 20, "cfg": 7.0,
                                             "width": 640, "height": 960, "batch": 2})
        self.assertEqual(applied["seed"], 9)
        self.assertEqual(self.prompt["7"]["inputs"]["steps"], 20)
        self.assertEqual(self.prompt["7"]["inputs"]["cfg"], 7.0)
        self.assertEqual(self.prompt["6"]["inputs"]["width"], 640)
        self.assertEqual(self.prompt["6"]["inputs"]["height"], 960)
        self.assertEqual(self.prompt["6"]["inputs"]["batch_size"], 2)

    def test_params_from_prompt(self):
        params = comfy_api.params_from_prompt(self.prompt, ["7"], ["4"], ["5"])
        self.assertEqual(params["sampler"]["seed"], 1234)
        self.assertEqual(params["sampler"]["steps"], 35)
        self.assertEqual(params["latent"], {"node_id": "6", "width": 832, "height": 1216,
                                           "batch": 1})
        self.assertEqual(params["text"]["positive"]["node_id"], "4")
        self.assertEqual(params["text"]["negative"]["node_id"], "5")

    def test_checkpoint_of(self):
        self.assertEqual(comfy_api.checkpoint_of(self.prompt), "a.safetensors")


class ClientTests(unittest.TestCase):
    def make_client(self):
        client = comfy_api.ComfyClient("http://127.0.0.1:9")
        return client

    def test_queue_prompt_ok(self):
        client = self.make_client()
        with mock.patch.object(client, "_request",
                               return_value={"prompt_id": "p-1", "number": 2,
                                             "node_errors": {}}):
            result = client.queue_prompt({"1": {"class_type": "X", "inputs": {}}})
        self.assertTrue(result["ok"])
        self.assertEqual(result["prompt_id"], "p-1")
        self.assertEqual(result["number"], 2)

    def test_queue_prompt_http_error(self):
        client = self.make_client()

        def boom(*_args, **_kwargs):
            payload = json.dumps({"error": {"type": "prompt_outputs_failed_validation"},
                                  "node_errors": {"7": {"errors": [{"message": "bad"}]}}})
            raise urllib.error.HTTPError("http://127.0.0.1:9/prompt", 400, "Bad",
                                         {}, mock.MagicMock(
                                             read=lambda: payload.encode("utf-8")))

        with mock.patch.object(client, "_request", side_effect=boom):
            result = client.queue_prompt({"1": {"class_type": "X", "inputs": {}}})
        self.assertFalse(result["ok"])
        self.assertIn("拒绝提交", result["error"])

    def test_queue_prompt_connection_error(self):
        client = self.make_client()
        with mock.patch.object(client, "_request", side_effect=OSError("refused")):
            result = client.queue_prompt({})
        self.assertFalse(result["ok"])
        self.assertIn("连不上", result["error"])

    def test_wait_done(self):
        client = self.make_client()
        entry = {"status": {"completed": True}, "outputs": {}}
        with mock.patch.object(client, "history",
                               side_effect=[{"ok": True, "data": {}},
                                            {"ok": True, "data": {"p-1": entry}}]):
            status, data = client.wait("p-1", timeout=5, interval=0.01)
        self.assertEqual(status, "done")
        self.assertEqual(data["entry"], entry)

    def test_wait_error(self):
        client = self.make_client()
        entry = {"status": {"completed": True, "status_str": "error",
                            "messages": [["execution_error", {"exception_message": "OOM",
                                                              "node_id": "7",
                                                              "node_type": "KSampler"}]]}}
        with mock.patch.object(client, "history",
                               return_value={"ok": True, "data": {"p-1": entry}}):
            status, data = client.wait("p-1", timeout=5, interval=0.01)
        self.assertEqual(status, "error")
        self.assertIn("OOM", data["error"])
        self.assertIn("KSampler", data["error"])

    def test_wait_timeout(self):
        client = self.make_client()
        with mock.patch.object(client, "history",
                               return_value={"ok": True, "data": {}}):
            status, data = client.wait("p-1", timeout=0.05, interval=0.02)
        self.assertEqual(status, "timeout")

    def test_images_from_history(self):
        entry = {"outputs": {"9": {"images": [{"filename": "a.png", "subfolder": "",
                                               "type": "output"}]},
                             "12": {"images": []}}}
        images = comfy_api.images_from_history(entry)
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]["node_id"], "9")
        self.assertEqual(images[0]["filename"], "a.png")

    def test_save_images(self):
        client = self.make_client()
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(client, "download_image", return_value=b"PNGDATA"):
                saved = comfy_api.save_images(client, "g-20260101-000000-abcd",
                                              [{"filename": "a.png", "subfolder": "",
                                                "type": "output"}], tmp)
            self.assertEqual(len(saved), 1)
            self.assertTrue(os.path.isfile(saved[0]["local"]))
            self.assertEqual(saved[0]["bytes"], len(b"PNGDATA"))
            with open(saved[0]["local"], "rb") as fh:
                self.assertEqual(fh.read(), b"PNGDATA")

    def test_save_images_download_error_is_kept(self):
        client = self.make_client()
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(client, "download_image", side_effect=OSError("boom")):
                saved = comfy_api.save_images(client, "g-x", [{"filename": "a.png"}], tmp)
            self.assertEqual(saved[0]["local"], "")
            self.assertIn("下载失败", saved[0]["error"])


class GenerationStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = history_store.HistoryStore(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_save_and_load(self):
        rec = self.store.save_generation("", {"workflow": "w.json", "positive": "p",
                                              "params": {"sampler": {"seed": 1}}})
        self.assertRegex(rec["generation_id"], history_store.GEN_RE)
        loaded = self.store.load_generation(rec["generation_id"])
        self.assertEqual(loaded["status"], "running")
        self.assertEqual(loaded["attempts"], 1)
        self.assertEqual(loaded["positive"], "p")

    def test_update_generation(self):
        rec = self.store.save_generation("", {"workflow": "w.json"})
        updated = self.store.update_generation(rec["generation_id"],
                                               {"status": "done", "duration_sec": 61.2})
        self.assertEqual(updated["status"], "done")
        self.assertEqual(updated["duration_sec"], 61.2)
        self.assertIn("updated_at", updated)

    def test_list_and_stats(self):
        self.store.save_generation("", {"workflow": "a"})
        self.store.save_generation("", {"workflow": "b"})
        self.assertEqual(len(self.store.list_generations()), 2)
        self.assertEqual(self.store.stats()["generations"], 2)

    def test_conversation_link(self):
        conv = self.store.create(title="出图测试")
        cid = conv["conversation_id"]
        self.store.save_generation(cid, {"workflow": "a"})
        conv2 = self.store.load(cid)
        self.assertEqual(len(conv2["generation_ids"]), 1)
        items = self.store.list_generations(cid)
        self.assertEqual(len(items), 1)
        self.assertEqual(self.store.list_generations("c-00000000-000000-0000"), [])

    def test_bad_id_rejected(self):
        self.assertIsNone(self.store.load_generation("../config"))
        self.assertIsNone(self.store.load_generation("g-xxx"))


class PublicGenerationTests(unittest.TestCase):
    def test_urls_instead_of_paths(self):
        rec = {"generation_id": "g-20260101-000000-abcd", "status": "done",
               "images": [{"local": r"D:\AI\out\01.png", "filename": "a.png", "bytes": 10}]}
        public = server.generation_public(rec)
        self.assertEqual(public["images"][0]["url"],
                         "/api/generations/g-20260101-000000-abcd/image/1")
        dumped = json.dumps(public, ensure_ascii=False)
        self.assertNotIn("D:\\AI", dumped)
        self.assertNotIn("local", public["images"][0])

    def test_missing_local_has_no_url(self):
        rec = {"generation_id": "g-20260101-000000-abcd", "status": "done",
               "images": [{"local": "", "filename": "a.png", "error": "下载失败"}]}
        public = server.generation_public(rec)
        self.assertEqual(public["images"][0]["url"], "")
        self.assertEqual(public["images"][0]["error"], "下载失败")


if __name__ == "__main__":
    unittest.main()
