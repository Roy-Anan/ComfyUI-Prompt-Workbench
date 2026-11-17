# -*- coding: utf-8 -*-
"""探针：ComfyUI 是否在跑、object_info 里我们需要的节点定义。"""
import json
import sys
import urllib.request

BASE = "http://127.0.0.1:8188"


def get(path, timeout=15):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    try:
        stats = get("/system_stats", 8)
        print("system_stats:", json.dumps(stats, ensure_ascii=False)[:300])
    except Exception as exc:
        print("system_stats 失败：", exc)
        return 1

    try:
        q = get("/queue", 8)
        print("queue: running=%s pending=%s" % (len(q.get("queue_running", [])),
                                              len(q.get("queue_pending", []))))
    except Exception as exc:
        print("queue 失败：", exc)

    try:
        info = get("/object_info", 60)
        print("object_info classes:", len(info))
        for cls in ("KSampler", "KSamplerAdvanced", "CheckpointLoaderSimple", "CLIPTextEncode",
                    "LoraLoader", "EmptyLatentImage", "SaveImage", "VAEDecode"):
            spec = info.get(cls)
            if not spec:
                print(cls, "→ 缺失")
                continue
            req = (spec.get("input") or {}).get("required") or {}
            opt = (spec.get("input") or {}).get("optional") or {}
            order = spec.get("input_order") or {}
            print("\n%s required=%s" % (cls, json.dumps(req, ensure_ascii=False)[:400]))
            if opt:
                print("   optional=%s" % json.dumps(opt, ensure_ascii=False)[:200])
            print("   order=%s" % json.dumps(order, ensure_ascii=False)[:200])
        with open(r"D:\AI\ComfyUI_Prompt_Workbench\logs\object_info.json", "w", encoding="utf-8") as fh:
            json.dump(info, fh, ensure_ascii=False)
        print("\n已保存 logs\\object_info.json")
    except Exception as exc:
        print("object_info 失败：", exc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
