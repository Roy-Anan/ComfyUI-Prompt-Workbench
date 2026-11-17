# -*- coding: utf-8 -*-
"""真实对话验证 + 输出质量检查（防重复死循环）。

起临时服务 → 用真实工作流注入 → 调一次 Ollama → 存完整回复 → 检查分段与重复。

运行：python tools\\chat_demo.py
"""

import json
import os
import re
import subprocess
import sys
import time
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
HOST = "http://127.0.0.1:8199"
PY = sys.executable
OUT = os.path.join(BASE, "logs", "对话样例_阶段2.txt")

PROMPT = "帮我给这个工作流出提示词：白发少女坐在窗边，午后逆光，半写实插画风，氛围安静"


def post(path, payload, timeout=15):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(HOST + path, data=data,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def wait_up(seconds=30):
    for _ in range(seconds * 4):
        try:
            urllib.request.urlopen(HOST + "/api/health", timeout=3).read()
            return True
        except Exception:
            time.sleep(0.25)
    return False


def analyse(content):
    sections = ["【当前模型】", "【Positive Prompt】", "【Negative Prompt】",
                "【Generation Settings】", "【模型适配说明】"]
    found = [s for s in sections if s in content]
    # 重复检查：只看 Negative 段，统计最高频英文标签出现次数
    neg = ""
    if "【Negative Prompt】" in content:
        neg = content.split("【Negative Prompt】", 1)[1]
        for stop in ("【Generation Settings】", "【模型适配说明】", "【待确认项】"):
            if stop in neg:
                neg = neg.split(stop, 1)[0]
    tags = [t.strip().lower() for t in re.split(r"[,，\n]", neg) if t.strip()]
    counts = {}
    for t in tags:
        counts[t] = counts.get(t, 0) + 1
    worst = max(counts.items(), key=lambda kv: kv[1]) if counts else ("", 0)
    return found, len(tags), worst


def main():
    proc = subprocess.Popen([PY, os.path.join(BASE, "app", "server.py")],
                            cwd=BASE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        if not wait_up():
            print("服务未起来")
            return 1
        print("对话中（首次加载模型约 1~2 分钟）…")
        t0 = time.time()
        reply = post("/api/chat", {
            "workflow": "suyuexisdxl.json",
            "messages": [{"role": "user", "content": PROMPT}],
        }, timeout=400)
        cost = time.time() - t0

        if not reply.get("ok"):
            print("失败：", reply.get("message"), reply.get("hint", ""))
            return 1

        content = reply.get("content", "")
        meta = reply.get("meta") or {}
        usage = reply.get("usage") or {}
        found, neg_count, worst = analyse(content)

        head = ("用时 %.1fs｜输出 %d 字符｜尝试 %s 次｜guard %s｜输入 token %s｜输出 token %s｜注入 %s 字符｜profile %s\n"
                "包含分段：%s\nnegative 标签数：%d｜最高重复：%s × %d\n%s\n"
                % (cost, len(content), reply.get("attempts", 1),
                   "ok" if (reply.get("guard") or {}).get("ok") else (reply.get("guard") or {}).get("reasons"),
                   usage.get("prompt_tokens"), usage.get("output_tokens"),
                   meta.get("injected_chars"), meta.get("profile_file"),
                   "、".join(found) or "（无）", neg_count, worst[0], worst[1],
                   "=" * 60))
        with open(OUT, "w", encoding="utf-8") as fh:
            fh.write(head + "\n" + content + "\n")

        print(head)
        print(content)
        print("=" * 60)
        ok = len(found) >= 4 and worst[1] <= 3 and neg_count <= 60 and len(content) < 8000
        print("质量结论：", "通过" if ok else "未达标（分段缺失 / 重复过高 / 负面标签超量 / 篇幅过长）")

        try:
            post("/api/unload", {}, timeout=20)
            print("已卸载模型")
        except Exception as exc:
            print("卸载失败：", exc)
        return 0 if ok else 2
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    sys.exit(main())
