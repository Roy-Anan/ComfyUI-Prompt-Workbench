# -*- coding: utf-8 -*-
"""探针：UI Workflow → API Prompt 转换结果检查（不提交）。"""
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from app import comfy_api, comfy_workflow  # noqa: E402

WF = r"D:\AI\Qiuye\ComfyUI-aki-v3.2\ComfyUI\user\default\workflows\suyuexisdxl.json"


def main():
    with open(os.path.join(BASE, "logs", "object_info.json"), encoding="utf-8") as fh:
        info = json.load(fh)
    ui = json.load(open(WF, encoding="utf-8"))
    prompt, warnings = comfy_api.convert_ui_to_api(ui, info)
    print("warnings:", warnings)
    for node_id, node in prompt.items():
        print(node_id, node["class_type"], json.dumps(node["inputs"], ensure_ascii=False)[:200])

    parsed = comfy_workflow.parse_workflow(WF)
    pos_ids = parsed["positive"]["node_ids"]
    neg_ids = parsed["negative"]["node_ids"]
    comfy_api.set_text_inputs(prompt, pos_ids, "a cat sitting on a windowsill, soft light")
    comfy_api.set_text_inputs(prompt, neg_ids, "lowres, blurry")
    sampler_ids = [s["node_id"] for s in parsed["samplers"]]
    applied = comfy_api.apply_overrides(prompt, sampler_ids, {"seed": 1234})
    print("applied:", applied)
    print("params:", json.dumps(comfy_api.params_from_prompt(prompt, sampler_ids, pos_ids, neg_ids),
                                ensure_ascii=False))
    print("checkpoint:", comfy_api.checkpoint_of(prompt))
    print("text nodes now:", [(i, n["inputs"].get("text")) for i, n in prompt.items()
                              if "text" in n["inputs"]])


if __name__ == "__main__":
    main()
