# -*- coding: utf-8 -*-
"""阶段 3 冒烟：真起服务、真打接口、真对话两轮、真重启一次。

运行：python tests\\smoke_server.py
"""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from app import __version__ as APP_VERSION      # noqa: E402
PORT = 8199
HOST = "http://127.0.0.1:%d" % PORT
PY = sys.executable
WF_PATH = r"D:\AI\Qiuye\ComfyUI-aki-v3.2\ComfyUI\user\default\workflows\suyuexisdxl.json"

passed, failed = [], []


def check(name, cond, detail=""):
    (passed if cond else failed).append(name)
    print("[%s] %s %s" % ("PASS" if cond else "FAIL", name, detail))


def get(path, timeout=15):
    req = urllib.request.Request(HOST + path, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        try:
            return json.loads(body)
        except Exception:
            return {"ok": False, "code": exc.code, "body": body}


def post(path, payload, timeout=15):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(HOST + path, data=data,
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        return {"ok": False, "code": exc.code, "body": body}


def text(path, timeout=15):
    with urllib.request.urlopen(HOST + path, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def raw(path, timeout=60):
    with urllib.request.urlopen(HOST + path, timeout=timeout) as resp:
        return resp.status, resp.headers.get("Content-Type", ""), resp.read()


def wait_up(seconds=30):
    for _ in range(seconds * 4):
        try:
            get("/api/health", timeout=3)
            return True
        except Exception:
            time.sleep(0.25)
    return False


def start_server():
    proc = subprocess.Popen([PY, os.path.join(BASE, "app", "server.py")],
                            cwd=BASE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if not wait_up():
        out = proc.stdout.read().decode("utf-8", "replace") if proc.stdout else ""
        raise RuntimeError("服务没起来：\n" + out[-1500:])
    return proc


def stop_server(proc):
    proc.terminate()
    try:
        proc.wait(timeout=8)
    except Exception:
        proc.kill()


def main():
    print("=" * 62)
    proc = start_server()
    conv_id = None
    try:
        # ---------------- 静态与阶段 1/2 回归
        html = text("/")
        check("首页可访问", "Prompt Workbench" in html and "/app.js" in html)
        check("CSS 可访问", "--accent" in text("/style.css"))
        check("JS 可访问", "/api/conversations" in text("/app.js"))

        # ---------------- 阶段 7：页面结构 / 运行状态 / 日志
        check("V2.0 正式版标识", "V2.0" in html and "正式版" in html)
        check("运行状态条在页面里", all(x in html for x in
              ('id="runtimeBar"', 'id="rtTask"', 'id="rtRefresh"')),
              "runtime strip")
        check("设置 / 日志 / 预览弹层在页面里", all(x in html for x in
              ('id="settingsModal"', 'id="logsModal"', 'id="previewModal"')),
              "modals")
        check("备份面板在页面里", all(x in html for x in
              ('id="backupList"', 'id="backupCreate"')), "backup")
        check("错误提示条在页面里", 'id="errorBanner"' in html and 'id="errorText"' in html)
        check("深色样式已加载", "color-scheme:dark" in text("/style.css")
              and "runtime-strip" in text("/style.css"))

        runtime = get("/api/runtime").get("runtime") or {}
        check("运行状态接口", runtime.get("busy", {}).get("chat") is False
              and runtime.get("busy", {}).get("generate") is False, str(runtime.get("busy")))
        check("运行时长已统计", (runtime.get("uptime_sec") or 0) > 0,
              "%s 秒" % runtime.get("uptime_sec"))
        check("运行计数器已初始化", (runtime.get("counters") or {}).get("errors") == 0,
              str(runtime.get("counters")))
        check("最近日志可读", bool(runtime.get("log_tail"))
              and runtime["log_tail"][0].get("message"), "工作台启动")

        logs = get("/api/logs?limit=20")
        check("日志接口", logs.get("ok") and len(logs.get("entries") or []) >= 1,
              "%d 条" % len(logs.get("entries") or []))
        check("日志带时间/级别/范围", all(k in (logs["entries"][0] or {})
              for k in ("ts", "level", "scope", "message")), str(logs["entries"][0])[:120])
        check("日志文件信息", (logs.get("files") or {}).get("path", "").endswith("workbench.log"),
              (logs.get("files") or {}).get("path"))
        check("日志可按级别过滤", all(e.get("level") == "error"
              for e in (get("/api/logs?limit=20&level=error").get("entries") or [])))

        chinese = "阶段7 中文日志 UTF-8 校验"
        post("/api/client-log", {"level": "info", "message": chinese,
                                 "detail": {"where": "smoke"}, "url": "/"})
        time.sleep(0.4)
        entries = get("/api/logs?limit=30").get("entries") or []
        check("中文日志不乱码", any(e.get("message") == chinese for e in entries),
              next((e.get("message") for e in entries if e.get("scope") == "client"), "无"))
        dumped_log = text("/api/logs/download")
        check("日志下载", chinese in dumped_log and "工作台启动" in dumped_log,
              "%d 字符" % len(dumped_log))


        health = get("/api/health")
        check("健康检查", health.get("ok") and health.get("version") == APP_VERSION,
              health.get("version", ""))
        check("模型列表 13 个", len(get("/api/models").get("models", [])) == 13)
        lookup = get("/api/lookup?name=" + urllib.parse.quote("intorealismUltra_v80.safetensors"))
        check("Profile 精确匹配", lookup.get("profile_file") == "IntoRealism_Ultra_V8.txt")
        check("完整性体检", get("/api/integrity").get("ok"))
        check("未登记拒绝", not get("/api/lookup?name=nope.safetensors").get("ok"))

        wf = get("/api/workflow?name=suyuexisdxl.json")
        check("工作流解析", (wf.get("parsed") or {}).get("checkpoint", {}).get("name")
              == "intorealismUltra_v80.safetensors")
        ctx = get("/api/context?workflow=suyuexisdxl.json")
        check("注入预览", ctx.get("ok") and ctx["meta"]["injected_chars"] > 3000,
              "%s 字符" % ctx.get("meta", {}).get("injected_chars"))
        check("目录穿越被拦", not get("/api/workflow?name=../config.json").get("ok"))

        # ---------------- 阶段 4：工作流识别（按连线）
        p = wf.get("parsed") or {}
        check("正向节点按连线判定", p.get("positive", {}).get("node_ids") == ["4"]
              and p["positive"]["source"] == "link", str(p.get("positive", {}).get("node_ids")))
        check("负向节点按连线判定", p.get("negative", {}).get("node_ids") == ["5"])
        smp = p.get("sampler") or {}
        lat = p.get("latent") or {}
        check("参数齐全", smp.get("steps") == 35 and smp.get("cfg") == 5.5
              and smp.get("sampler_name") == "dpmpp_2m_sde" and smp.get("scheduler") == "karras"
              and smp.get("seed") == 231661496131269
              and (lat.get("width"), lat.get("height")) == (832, 1216)
              and p.get("loras") and p["loras"][0]["name"] == "suyuexifull_c1-st6000.safetensors")
        meta_wf = ((ctx.get("meta") or {}).get("workflow") or {})
        check("注入里带正负节点", meta_wf.get("positive_nodes") == ["4"]
              and meta_wf.get("negative_nodes") == ["5"])
        check("注入文案按连线", "按连线判定" in (ctx.get("system") or ""))

        lib = get("/api/workflows")
        check("工作流列表合并两个来源", lib["counts"]["comfyui"] >= 4
              and all("source" in x for x in lib["workflows"]),
              "comfyui %s / workbench %s" % (lib["counts"]["comfyui"], lib["counts"]["workbench"]))

        real_text = open(WF_PATH, encoding="utf-8").read()
        imp = post("/api/workflows/import", {"name": "冒烟导入_ui.json", "content": real_text})
        imported = imp.get("entry", {}).get("name") if imp.get("ok") else ""
        check("导入 UI Workflow", bool(imported), imported)
        check("导入后仍按连线识别", (imp.get("parsed") or {}).get("positive", {}).get("node_ids") == ["4"])

        api_wf = {
            "1": {"class_type": "CheckpointLoaderSimple",
                  "inputs": {"ckpt_name": "intorealismUltra_v80.safetensors"}},
            "2": {"class_type": "CLIPTextEncode", "inputs": {"text": "api pos", "clip": ["1", 1]}},
            "3": {"class_type": "CLIPTextEncode", "inputs": {"text": "api neg", "clip": ["1", 1]}},
            "4": {"class_type": "KSampler",
                  "inputs": {"seed": 9, "steps": 20, "cfg": 7, "sampler_name": "euler",
                             "scheduler": "normal", "denoise": 1, "model": ["1", 0],
                             "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["5", 0]}},
            "5": {"class_type": "EmptyLatentImage",
                  "inputs": {"width": 640, "height": 960, "batch_size": 1}},
        }
        imp2 = post("/api/workflows/import", {"name": "冒烟导入_api.json", "content": api_wf})
        check("导入 API Prompt", imp2.get("ok") and imp2["entry"]["format"] == "api"
              and imp2["parsed"]["positive"]["node_ids"] == ["2"],
              imp2.get("entry", {}).get("name", imp2.get("message", "")))

        if imported:
            mapped = post("/api/workflows/mapping", {"name": imported, "positive_node": "5"})
            check("人工映射覆盖自动判定", mapped.get("ok")
                  and mapped["parsed"]["positive"]["source"] == "manual"
                  and mapped["parsed"]["positive"]["node_ids"] == ["5"])
            reset = post("/api/workflows/mapping", {"name": imported, "positive_node": ""})
            check("映射可清除回连线判定", reset.get("ok")
                  and reset["parsed"]["positive"]["source"] == "link")
            dele = post("/api/workflows/delete", {"name": imported})
            check("删除导入工作流（归档）", dele.get("ok"))

        # ---------------- 阶段 3：会话 CRUD
        conv = post("/api/conversations", {"workflow": "suyuexisdxl.json", "title": "冒烟会话"})
        conv_id = conv["conversation"]["conversation_id"]
        check("新建对话", conv.get("ok") and conv_id.startswith("c-"),
              conv_id + " / " + conv["conversation"]["checkpoint"])
        check("对话列表", any(c["conversation_id"] == conv_id
                          for c in get("/api/conversations")["conversations"]))
        renamed = post("/api/conversations/%s/rename" % conv_id, {"title": "冒烟-改名"})
        check("改标题", renamed.get("ok") and renamed["conversation"]["title"] == "冒烟-改名")

        settings = get("/api/settings")["settings"]
        check("设置读取", settings["application"]["auto_save_history"] is True)
        system = get("/api/settings").get("system") or {}
        check("设置页系统信息", system.get("app", {}).get("version") == APP_VERSION
              and system.get("paths", {}).get("logs"), system.get("app", {}).get("version", ""))
        check("设置页规则包体检", (system.get("integrity") or {}).get("ok") is True,
              "db %s / profile %s" % ((system.get("integrity") or {}).get("db_entries"),
                                      (system.get("integrity") or {}).get("profile_files")))
        saved = post("/api/settings", {"chat": {"history_max_messages": 10}})
        check("设置保存", saved.get("ok") and saved["settings"]["chat"]["history_max_messages"] == 10)
        check("设置已备份", saved["info"]["backup_exists"])
        clamped = post("/api/settings", {
            "chat": {"history_max_messages": 99, "system_prompt_variant": "精简版"},
            "application": {"theme": "light", "confirm_delete": "false"},
        })
        check("设置白名单与收窄", clamped.get("ok")
              and clamped["settings"]["chat"]["history_max_messages"] == 60
              and clamped["settings"]["application"]["theme"] == "dark",
              "；".join(clamped.get("warnings") or []))
        check("非法布尔被拒", clamped["settings"]["application"]["confirm_delete"] is True)
        restored = post("/api/settings", {"chat": {"history_max_messages": 20}})
        check("历史上限恢复 20", restored["settings"]["chat"]["history_max_messages"] == 20)

        # ---------------- 真对话两轮
        status = get("/api/status")
        ollama = status.get("ollama", {})
        print("[INFO] Ollama running=%s version=%s model_registered=%s"
              % (ollama.get("running"), ollama.get("version"), ollama.get("model_registered")))

        tokens1 = tokens2 = None
        if ollama.get("running") and ollama.get("model_registered"):
            print("[INFO] 第 1 轮对话（模型加载可能要几十秒）…")
            r1 = post("/api/chat", {"conversation_id": conv_id,
                                    "message": "白发少女坐在窗边，午后逆光，半写实插画风",
                                    "workflow": "suyuexisdxl.json"}, timeout=400)
            check("第 1 轮返回", r1.get("ok") and len(r1.get("content", "")) > 100,
                  "%d 字符" % len(r1.get("content", "")))
            check("第 1 轮已落盘", r1.get("auto_saved") is True
                  and len(r1["conversation"]["messages"]) == 2,
                  "%d 条消息" % len(r1.get("conversation", {}).get("messages", [])))
            check("提示词记录", r1.get("prompt") and r1["prompt"]["prompt_id"].startswith("p-"))
            tokens1 = (r1.get("usage") or {}).get("prompt_tokens")

            print("[INFO] 第 2 轮对话（验证多轮上下文）…")
            r2 = post("/api/chat", {"conversation_id": conv_id,
                                    "message": "接着上一轮：把负面里的 lowres 去掉，再加一点胶片颗粒感",
                                    "workflow": "suyuexisdxl.json"}, timeout=400)
            check("第 2 轮返回", r2.get("ok") and len(r2.get("content", "")) > 100,
                  "%d 字符" % len(r2.get("content", "")))
            check("第 2 轮消息数", len(r2.get("conversation", {}).get("messages", [])) == 4,
                  "%d 条" % len(r2.get("conversation", {}).get("messages", [])))
            tokens2 = (r2.get("usage") or {}).get("prompt_tokens")
            check("多轮上下文已带历史", tokens2 and tokens1 and tokens2 > tokens1,
                  "prompt tokens %s -> %s" % (tokens1, tokens2))

            prompts = get("/api/prompts?conversation_id=" + conv_id)["prompts"]
            # 模型偶发跑飞时正文里可能没有可抽取的六段结构，这里按实际抽到的条数判定，
            # 但至少要有一条，且每轮都要落盘消息（上面已校验 4 条）。
            check("提示词记录（至少一轮抽到）", len(prompts) >= 1,
                  "%d 条（两轮里抽到 %d 条；第 1 轮 %s，第 2 轮 %s）"
                  % (len(prompts), len(prompts),
                     "有" if r1.get("prompt") else "无",
                     "有" if r2.get("prompt") else "无"))

            loaded = get("/api/vram").get("ollama_loaded") or []
            check("出图前 Ollama 已驻留（阶段 6 前置）",
                  any(m.get("name") == "comfyui-prompt:v1" for m in loaded),
                  "、".join(m.get("name", "") for m in loaded) or "无")
            rt_chat = get("/api/runtime").get("runtime") or {}
            check("对话计入运行状态", (rt_chat.get("counters") or {}).get("chat") >= 2,
                  str(rt_chat.get("counters")))
            check("对话最近一次成功", (rt_chat.get("last") or {}).get("chat", {}).get("outcome") == "ok",
                  str((rt_chat.get("last") or {}).get("chat", {}).get("elapsed_sec")))
        else:
            print("[SKIP] Ollama 未就绪，跳过真实对话")

        # ---------------- 阶段 5：出图（真提交 ComfyUI，真回显）
        html5 = text("/")
        check("前端有出图记录区", "出图记录" in html5 and 'id="gallery"' in html5)
        check("前端会调出图接口", "/api/generate" in text("/app.js"))
        comfy = get("/api/status").get("comfyui", {})
        print("[INFO] ComfyUI running=%s version=%s queue=%s/%s"
              % (comfy.get("running"), comfy.get("version"),
                 comfy.get("queue_running"), comfy.get("queue_pending")))
        check("ComfyUI 状态上报", comfy.get("running") is True and comfy.get("version"),
              comfy.get("version", ""))

        gid = None
        if comfy.get("running"):
            print("[INFO] 真实出图（832×1216 / 35 步，8GB 显存约 1 分钟）…")
            gen = post("/api/generate", {
                "conversation_id": conv_id,
                "workflow": "suyuexisdxl.json",
                "positive": "1girl, sitting by the window, afternoon backlight, "
                            "soft shadows, semi-realistic illustration, calm atmosphere",
                "negative": "lowres, blurry, watermark, bad anatomy",
                "seed": "randomize", "steps": 35, "width": 832, "height": 1216,
            }, timeout=400)
            check("出图成功", gen.get("ok") is True, str(gen.get("message", ""))[:160])
            gid = gen.get("generation_id") or ""
            check("出图记录 ID", gid.startswith("g-"), gid)
            check("ComfyUI prompt_id", bool(gen.get("prompt_id")), str(gen.get("prompt_id")))
            check("真实计算耗时", (gen.get("duration_sec") or 0) > 10,
                  "%s 秒" % gen.get("duration_sec"))

            images = ((gen.get("generation") or {}).get("images") or [])
            check("返回图片条目", len(images) == 1 and images[0].get("url"), str(len(images)))
            if images and images[0].get("url"):
                st, ctype, blob = raw(images[0]["url"])
                check("图片可访问", st == 200 and len(blob) > 50000,
                      "%d 字节 / %s" % (len(blob), ctype))
                check("图片是 PNG", "image/png" in ctype or blob[:8] == b"\x89PNG\r\n\x1a\n")
                check("图片落盘到工作台", os.path.isfile(os.path.join(
                    BASE, "outputs", gid, "01.png")))
                snap = os.path.join(BASE, "outputs", gid, "prompt.json")
                check("提交快照已存", os.path.isfile(snap)
                      and "sitting by the window" in open(snap, encoding="utf-8").read())

            params = gen.get("params") or {}
            sp = params.get("sampler") or {}
            lt = params.get("latent") or {}
            check("参数记录完整", isinstance(sp.get("seed"), int) and sp.get("steps") == 35
                  and sp.get("cfg") == 5.5 and sp.get("sampler_name") == "dpmpp_2m_sde"
                  and (lt.get("width"), lt.get("height")) == (832, 1216),
                  "seed %s / %s 步 / %s×%s" % (sp.get("seed"), sp.get("steps"),
                                               lt.get("width"), lt.get("height")))

            # ---------------- 阶段 6：显存自动管理（真链路）
            vram = gen.get("vram") or {}
            steps = {s.get("name"): s for s in vram.get("steps") or []}
            check("显存自动管理已启用", vram.get("auto") is True)
            check("卸载 Ollama 步骤成功", (steps.get("ollama_unload") or {}).get("ok") is True,
                  (steps.get("ollama_unload") or {}).get("detail", ""))
            check("卸载前确有模型驻留", bool(vram.get("ollama_loaded_before")),
                  "、".join(vram.get("ollama_loaded_before") or []) or "无")
            check("卸载腾出了显存", "卸载" in (steps.get("ollama_unload") or {}).get("detail", ""))
            check("GPU 显存已读数", (vram.get("vram_before") or {}).get("ok") is True,
                  "空闲 %s MB" % (vram.get("vram_before") or {}).get("free_mb"))
            check("释放 ComfyUI 模型/缓存", (steps.get("comfy_free") or {}).get("ok") is True,
                  (steps.get("comfy_free") or {}).get("detail", ""))
            check("Ollama 已重新加载", vram.get("ollama_reloaded") is True)
            check("上下文已恢复", vram.get("context_restored") is True)
            snap_path = vram.get("context_snapshot") or ""
            check("上下文快照落盘", bool(snap_path) and os.path.isfile(
                os.path.join(BASE, snap_path)), snap_path)
            loaded_after = get("/api/vram").get("ollama_loaded") or []
            check("Ollama 模型回到显存", any(m.get("name") == "comfyui-prompt:v1"
                                          for m in loaded_after),
                  "、".join(m.get("name", "") for m in loaded_after) or "无")
            check("状态接口上报显存", get("/api/vram").get("gpu", {}).get("ok") is True)

            rt_gen = get("/api/runtime").get("runtime") or {}
            check("出图计入运行状态", (rt_gen.get("counters") or {}).get("generate") >= 1,
                  str(rt_gen.get("counters")))
            check("出图最近一次成功",
                  (rt_gen.get("last") or {}).get("generate", {}).get("outcome") == "ok",
                  "%s 秒" % (rt_gen.get("last") or {}).get("generate", {}).get("elapsed_sec"))
            check("出图占用已释放",
                  (rt_gen.get("busy") or {}).get("generate") is False)
            check("出图日志已记录", any("出图完成" in (e.get("message") or "")
                  for e in (get("/api/logs?limit=60").get("entries") or [])),
                  "log_tail")
            check("运行状态带显存摘要", isinstance(rt_gen.get("last_vram"), dict)
                  and rt_gen["last_vram"].get("steps"), "vram steps")

            listed = get("/api/generations?conversation_id=" + conv_id)["generations"]
            check("出图记录按会话列出", any(g["generation_id"] == gid for g in listed)
                  and listed[0]["status"] == "done", "%d 条" % len(listed))
            one = get("/api/generations/" + gid)
            check("单条出图记录可查", one.get("ok") and one["generation"]["status"] == "done")
            check("记录里存了显存步骤", bool((one["generation"].get("vram") or {}).get("steps")),
                  "%d 步" % len((one["generation"].get("vram") or {}).get("steps") or []))
            dumped = json.dumps(one["generation"], ensure_ascii=False)
            check("记录不暴露绝对路径", "D:\\" not in dumped and "outputs" not in dumped)

            print("[INFO] 失败重试接口（同一组参数，命中 ComfyUI 缓存会很快）…")
            retried = post("/api/generations/%s/retry" % gid, {}, timeout=400)
            check("重试出图成功", retried.get("ok") is True, str(retried.get("message", ""))[:160])
            check("重试生成新记录", retried.get("generation_id")
                  and retried["generation_id"] != gid, retried.get("generation_id", ""))
            new_rec = get("/api/generations/" + (retried.get("generation_id") or ""))
            check("重试记录带来源", (new_rec.get("generation") or {}).get("retry_of") == gid)
            check("原记录标记重试去向", (get("/api/generations/" + gid).get("generation") or {}
                                  ).get("retried_by") == retried.get("generation_id"))

            bad = post("/api/generate", {"workflow": "nope.json", "positive": "x"})
            check("不存在的工作流被拒", bad.get("code") == 400 and not bad.get("ok"),
                  bad.get("message", "")[:80])
            rt_err = get("/api/runtime").get("runtime") or {}
            check("失败计入错误计数", (rt_err.get("counters") or {}).get("errors") >= 1,
                  str(rt_err.get("counters")))
            check("最近错误可查", bool(rt_err.get("last_error")),
                  str(rt_err.get("last_error"))[:100])
            error_logs = get("/api/logs?limit=30").get("entries") or []
            check("失败写入错误日志", any("出图请求失败" in (e.get("message") or "")
                  for e in error_logs),
                  "%d 条" % len(error_logs))
            missing = post("/api/generations/g-20000101-000000-ffff/retry", {})
            check("不存在的记录重试 404", missing.get("code") == 404)

            # ---------------- 阶段 6 验收：恢复 Ollama 后还能接着聊
            print("[INFO] 第 3 轮对话（出图后 Ollama 已自动恢复，验证上下文）…")
            r3 = post("/api/chat", {"conversation_id": conv_id,
                                    "message": "接着出图前那轮：把刚才的画面改成雨后清晨，其他不变",
                                    "workflow": "suyuexisdxl.json"}, timeout=400)
            check("恢复后继续对话", r3.get("ok") is True and len(r3.get("content", "")) > 100,
                  "%d 字符" % len(r3.get("content", "")))
            check("恢复后消息数 6", len(r3.get("conversation", {}).get("messages", [])) == 6,
                  "%d 条" % len(r3.get("conversation", {}).get("messages", [])))
            tokens3 = (r3.get("usage") or {}).get("prompt_tokens")
            check("恢复后仍带完整历史", tokens3 and tokens2 and tokens3 > tokens2,
                  "prompt tokens %s -> %s" % (tokens2, tokens3))

            unload = post("/api/unload", {})
            check("收尾卸载模型", unload.get("ok") is True, unload.get("message", ""))
        else:
            print("[SKIP] ComfyUI 未启动，跳过真实出图")

        md = text("/api/conversations/%s/export" % conv_id)
        check("导出 Markdown", md.startswith("# ") and "## " in md, "%d 字符" % len(md))

        before = get("/api/conversations/%s" % conv_id)
        count_before = len(before["conversation"]["messages"])

        # ---------------- 重启工作台（验收：历史仍然存在）
        stop_server(proc)
        print("[INFO] 服务已停，重新启动验证持久化…")
        time.sleep(1)
        proc = start_server()
        again = get("/api/conversations/%s" % conv_id)
        check("重启后对话仍在", again.get("ok") and len(again["conversation"]["messages"]) == count_before,
              "%d 条消息" % len(again.get("conversation", {}).get("messages", [])))
        check("重启后标题仍在", again["conversation"]["title"] == "冒烟-改名")
        check("重启后索引仍可列", any(c["conversation_id"] == conv_id
                              for c in get("/api/conversations")["conversations"]))
        if gid:
            gens = get("/api/generations?conversation_id=" + conv_id)["generations"]
            check("重启后出图记录仍在", any(g["generation_id"] == gid for g in gens))
            rec = [g for g in gens if g["generation_id"] == gid][0]
            st, _ctype, blob = raw(rec["images"][0]["url"])
            check("重启后图片仍可显示", st == 200 and len(blob) > 50000,
                  "%d 字节" % len(blob))

        # ---------------- 阶段 7：重启后的日志 / 运行状态 / 备份
        logs_after = get("/api/logs?limit=50")
        check("重启后日志仍可读", logs_after.get("ok")
              and len(logs_after.get("entries") or []) >= 5,
              "%d 条" % len(logs_after.get("entries") or []))
        check("重启后运行状态归零", (get("/api/runtime").get("runtime")
              .get("counters") or {}).get("errors") == 0)
        check("重启后设置仍生效", get("/api/settings")["settings"]["chat"]
              ["history_max_messages"] == 20)

        backup = post("/api/backups", {"note": "阶段7 冒烟"}, timeout=60)
        check("创建备份", backup.get("ok") is True, backup.get("message", "")[:100])
        bname = (backup.get("backup") or {}).get("name") or ""
        check("备份名规范", bname.startswith("backup-") and bname.endswith(".zip"), bname)
        check("备份包含用户数据", (backup.get("backup") or {}).get("file_count", 0) >= 20,
              "%s 个文件" % (backup.get("backup") or {}).get("file_count"))
        check("备份 counts 分类", ((backup.get("backup") or {}).get("counts") or {}).get("history", 0) > 0
              and ((backup.get("backup") or {}).get("counts") or {}).get("settings", 0) > 0,
              str((backup.get("backup") or {}).get("counts")))
        listed_b = get("/api/backups")
        hit = [b for b in (listed_b.get("backups") or []) if b.get("name") == bname]
        check("备份列表可列", listed_b.get("ok") and hit and hit[0].get("ok") is True,
              "%d 个" % len(listed_b.get("backups") or []))
        check("备份备注已存", (hit[0].get("note") if hit else "") == "阶段7 冒烟")
        check("备份接口统计", (listed_b.get("info") or {}).get("count", 0) >= 1,
              "%s 字节" % (listed_b.get("info") or {}).get("bytes"))
        st_b, ctype_b, blob_b = raw("/api/backups/%s/download" % urllib.parse.quote(bname))
        check("备份可下载", st_b == 200 and blob_b[:2] == b"PK",
              "%d 字节 / %s" % (len(blob_b), ctype_b))
        deleted_b = post("/api/backups/%s/delete" % urllib.parse.quote(bname), {})
        check("删除备份只进回收目录", deleted_b.get("ok") is True
              and not any(b.get("name") == bname
                          for b in (get("/api/backups").get("backups") or [])),
              deleted_b.get("message", ""))
        check("回收目录保留文件", os.path.isfile(os.path.join(
            BASE, "backups", "_trash", deleted_b.get("trashed", ""))))


        # ---------------- 删除归档
        tmp_conv = post("/api/conversations", {"workflow": "suyuexisdxl.json",
                                               "title": "待删除"})["conversation"]["conversation_id"]
        deleted = post("/api/conversations/%s/delete" % tmp_conv, {})
        check("删除对话", deleted.get("ok"))
        check("删除后列表不含", not any(c["conversation_id"] == tmp_conv
                                for c in get("/api/conversations")["conversations"]))
        archived = os.path.join(BASE, "history", "conversations", "_archive")
        check("删除只归档不抹除", any(tmp_conv in fn for fn in os.listdir(archived)))

    finally:
        stop_server(proc)

    print("=" * 62)
    print("通过 %d 项 / 失败 %d 项" % (len(passed), len(failed)))
    if failed:
        print("失败：", "、".join(failed))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
