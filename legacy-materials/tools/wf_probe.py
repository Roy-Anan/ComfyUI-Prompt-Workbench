# -*- coding: utf-8 -*-
"""打印真实工作流解析结果（阶段 4 手工核对用）。"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from app import comfy_workflow  # noqa: E402

P = r"D:\AI\Qiuye\ComfyUI-aki-v3.2\ComfyUI\user\default\workflows\suyuexisdxl.json"
parsed = comfy_workflow.parse_workflow(P)
print("format:", parsed["format"])
print("checkpoint:", parsed["checkpoint"])
print("positive nodes:", parsed["positive"]["node_ids"], "source:", parsed["positive"]["source"])
print("positive text:", parsed["positive"]["text"][:120])
print("negative nodes:", parsed["negative"]["node_ids"])
print("negative text:", parsed["negative"]["text"][:120])
print("loras:", parsed["loras"])
print("sampler:", parsed["sampler"])
print("latent:", parsed["latent"])
print("warnings:", parsed["warnings"])
print("---")
print(comfy_workflow.summarize(parsed))
