# -*- coding: utf-8 -*-
"""一次性验证：转换 → 提交 → 轮询 → 下载图片（不经过 web 服务）。"""
import json
import os
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from app import comfy_api, comfy_workflow  # noqa: E402

WF = r"D:\AI\Qiuye\ComfyUI-aki-v3.2\ComfyUI\user\default\workflows\suyuexisdxl.json"


def main():
    client = comfy_api.ComfyClient()
    stats = client.system_stats()
    print("comfy:", stats.get("ok"), (stats.get("data") or {}).get("system", {}).get("comfyui_version"))
    ui = json.load(open(WF, encoding="utf-8"))
    info = client.object_info()
    prompt, warnings = comfy_api.convert_ui_to_api(ui, info)
    print("warnings:", warnings)
    parsed = comfy_workflow.parse_workflow(WF)
    pos_ids, neg_ids = parsed["positive"]["node_ids"], parsed["negative"]["node_ids"]
    comfy_api.set_text_inputs(prompt, pos_ids,
                              "1girl, sitting by the window, afternoon backlight, soft shadows, "
                              "semi-realistic illustration, calm atmosphere")
    comfy_api.set_text_inputs(prompt, neg_ids, "lowres, blurry, watermark, bad anatomy")
    sampler_ids = [s["node_id"] for s in parsed["samplers"]]
    comfy_api.apply_overrides(prompt, sampler_ids, {"seed": 20261115})

    submit = client.queue_prompt(prompt)
    print("submit:", submit)
    if not submit.get("ok"):
        return 1
    pid = submit["prompt_id"]
    started = time.time()
    status, data = client.wait(pid, timeout=300, interval=1.5)
    print("wait:", status, "%.1fs" % (time.time() - started))
    if status != "done":
        print(json.dumps(data, ensure_ascii=False)[:1000])
        return 1
    images = comfy_api.images_from_history(data.get("entry"))
    print("images:", images)
    saved = comfy_api.save_images(client, "_probe", images,
                                  os.path.join(BASE, "outputs"))
    for item in saved:
        print("saved:", item.get("local"), item.get("bytes"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
