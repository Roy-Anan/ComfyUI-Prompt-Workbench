# -*- coding: utf-8 -*-
"""ComfyUI Prompt Workbench —— 阶段 5 服务端。

只监听 127.0.0.1，只用标准库。

页面 / 静态
  GET  /  /style.css  /app.js

状态与规则（阶段 1、2）
  GET  /api/health
  GET  /api/status
  GET  /api/models
  GET  /api/lookup?name=
  GET  /api/integrity
  GET  /api/workflows                    工作流列表（ComfyUI 目录 + 工作台库）
  POST /api/workflows/import             导入 UI / API JSON
  GET  /api/workflow?name=               解析（正负节点按连线判定）
  POST /api/workflows/mapping            人工节点映射
  POST /api/workflows/delete             删除工作台导入的工作流（归档）
  GET  /api/context?checkpoint=&workflow=

对话与历史（阶段 3）
  GET    /api/conversations                对话列表
  POST   /api/conversations                新建对话
  GET    /api/conversations/<id>           读取整段对话
  POST   /api/conversations/<id>/rename    改标题
  POST   /api/conversations/<id>/delete    删除（移到 _archive，不直接抹掉）
  GET    /api/conversations/<id>/export    导出 Markdown
  GET    /api/prompts?conversation_id=     提示词记录
  GET    /api/settings                     设置
  POST   /api/settings                     保存设置（写前备份）
  POST   /api/chat                         对话（服务端读盘续上下文，自动落盘）
  POST   /api/unload                       卸载 Ollama 模型

出图（阶段 5）
  POST /api/generate                       提交 ComfyUI 出图（UI → API 转换）
  POST /api/generations/<gid>/retry        失败重试
  GET  /api/generations?conversation_id=   出图记录
  GET  /api/generations/<gid>              单条记录
  GET  /api/generations/<gid>/image/<n>    回显图片（本地副本）
"""

from __future__ import annotations

import json
import mimetypes
import os
import random
import sys
import threading
import time
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app import __version__                                  # noqa: E402
from app import (backup, comfy_api, comfy_workflow, output_guard, prompt_extract,
                 runtime_state, vram_manager, workbench_log)  # noqa: E402
from app.history_store import HistoryStore                   # noqa: E402
from app.ollama_client import OllamaClient                   # noqa: E402
from app.profile_lookup import ProfileLookup                 # noqa: E402
from app.prompt_context import ContextBuilder                # noqa: E402
from app.settings_store import SettingsStore                 # noqa: E402
from app.workflow_lib import WorkflowLibrary                 # noqa: E402

WEB_DIR = os.path.join(BASE_DIR, "web")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")


def load_config():
    defaults = {
        "app": {"name": "ComfyUI Prompt Workbench", "version": __version__,
                "host": "127.0.0.1", "port": 8199},
        "ollama": {"base_url": "http://127.0.0.1:11434", "model": "comfyui-prompt:v1",
                   "keep_alive": "30m", "timeout": 240},
        "comfyui": {"base_url": "http://127.0.0.1:8188", "models_dir": "",
                    "workflows_dir": "", "loras_dir": ""},
        "workbench": {"default_workflow": "", "system_prompt_variant": "精简版",
                      "history_max_messages": 20},
        "vram": dict(vram_manager.DEFAULT_CONFIG),
        "hardware": {}, "application": {},
    }
    try:
        with open(CONFIG_PATH, encoding="utf-8-sig") as fh:
            loaded = json.load(fh)
    except FileNotFoundError:
        return defaults
    except Exception as exc:
        print("[warn] config.json 解析失败，使用默认值：%s" % exc)
        return defaults

    for section, values in defaults.items():
        if isinstance(values, dict):
            loaded.setdefault(section, {})
            for key, val in values.items():
                loaded[section].setdefault(key, val)
    return loaded


CONFIG = load_config()
LOOKUP = ProfileLookup()
HISTORY = HistoryStore(BASE_DIR)
SETTINGS = SettingsStore(BASE_DIR)

OLLAMA_CONF = CONFIG.get("ollama", {}) or {}
COMFY_CONF = CONFIG.get("comfyui", {}) or {}
WB_CONF = CONFIG.get("workbench", {}) or {}

OLLAMA = OllamaClient(
    base_url=OLLAMA_CONF.get("base_url"),
    model=OLLAMA_CONF.get("model"),
    keep_alive=OLLAMA_CONF.get("keep_alive", "30m"),
    timeout=int(OLLAMA_CONF.get("timeout", 240)),
    options=OLLAMA_CONF.get("options") or {},
)

CONTEXT = None
WORKFLOWS_DIR = COMFY_CONF.get("workflows_dir", "") or ""
LIB = WorkflowLibrary(BASE_DIR, WORKFLOWS_DIR)
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
COMFY_TIMEOUT = int(COMFY_CONF.get("timeout") or 300)
COMFY = comfy_api.ComfyClient(base_url=COMFY_CONF.get("base_url"),
                              timeout=int(COMFY_CONF.get("http_timeout") or 30))
VRAM_CONF = CONFIG.get("vram", {}) or {}
VRAM = vram_manager.VramSession(HISTORY, OLLAMA, COMFY, VRAM_CONF)
GENERATION_LOCK = threading.Lock()
LAST_VRAM = {}
LOGGER = workbench_log.WorkbenchLog(BASE_DIR)
BACKUPS = backup.BackupManager(BASE_DIR)
RUNTIME = runtime_state.RuntimeState()


def log_event(level, scope, message, **fields):
    return LOGGER.log(level, scope, message, **fields)


def keep_vram_summary(summary):
    global LAST_VRAM
    LAST_VRAM = summary or {}
    return LAST_VRAM


def vram_safe(name, func, *args, **kwargs):
    """显存步骤不能把一次已经成功的出图带崩；异常记进 steps 后继续。"""
    try:
        return func(*args, **kwargs)
    except Exception as exc:
        VRAM.errors.append("%s 异常：%s: %s" % (name, type(exc).__name__, exc))
        VRAM._record(name + "_error", False, "%s: %s" % (type(exc).__name__, exc))
        return VRAM.summary()


def refresh_context():
    global CONTEXT
    current = SETTINGS.load()
    variant = (current.get("chat", {}) or {}).get("system_prompt_variant") \
        or WB_CONF.get("system_prompt_variant", "精简版")
    CONTEXT = ContextBuilder(BASE_DIR, LOOKUP, loras_dir=COMFY_CONF.get("loras_dir", ""),
                             system_variant=variant)


refresh_context()


def history_limit():
    current = SETTINGS.load()
    return int((current.get("chat", {}) or {}).get("history_max_messages") or 20)


def settings_system():
    """设置页“系统信息”用：路径、服务、显存、体检、备份、日志。"""
    return {
        "app": {"name": CONFIG["app"]["name"], "version": __version__,
                "base_dir": BASE_DIR, "config_path": CONFIG_PATH},
        "ollama": {"base_url": OLLAMA.base_url, "model": OLLAMA.model,
                   "keep_alive": OLLAMA.keep_alive},
        "comfyui": {"base_url": COMFY_CONF.get("base_url", ""),
                    "workflows_dir": COMFY_CONF.get("workflows_dir", ""),
                    "models_dir": COMFY_CONF.get("models_dir", ""),
                    "loras_dir": COMFY_CONF.get("loras_dir", "")},
        "vram": {k: VRAM_CONF.get(k, vram_manager.DEFAULT_CONFIG.get(k))
                 for k in vram_manager.DEFAULT_CONFIG},
        "paths": {"history": os.path.join(BASE_DIR, "history"),
                  "settings": SETTINGS.dir,
                  "outputs": OUTPUTS_DIR,
                  "workflows": LIB.lib_dir,
                  "backups": BACKUPS.dir,
                  "logs": LOGGER.dir},
        "history": HISTORY.stats(),
        "settings": SETTINGS.info(),
        "backups": BACKUPS.info(),
        "logs": LOGGER.details(),
        "integrity": LOOKUP.integrity(checkpoints_dir=COMFY_CONF.get("models_dir") or None),
    }


def runtime_public():
    snap = RUNTIME.snapshot()
    snap["generation_lock"] = GENERATION_LOCK.locked()
    snap["server_time"] = datetime.now().astimezone().isoformat(timespec="seconds")
    snap["last_vram"] = LAST_VRAM
    snap["log_tail"] = LOGGER.recent(limit=5)
    snap["last_error_log"] = LOGGER.last_error()
    return snap


def list_workflows():
    return LIB.list_all()


def workflow_path(name):
    source, path = LIB.resolve(name)
    return path


def workflow_mapping(name):
    return LIB.load_mapping(os.path.basename(str(name or "").replace("\\", "/")))


def comfy_status():
    stats = COMFY.system_stats()
    queue = COMFY.queue_state()
    version = ((stats.get("data") or {}).get("system") or {}).get("comfyui_version", "") \
        if stats.get("ok") else ""
    return {"ok": stats.get("ok", False), "version": version,
            "queue_running": len(queue.get("running") or []),
            "queue_pending": len(queue.get("pending") or []),
            "error": stats.get("error", "")}


def _save_prompt_snapshot(gid, prompt, positive, negative):
    """把这次真正提交的 API Prompt 存一份，方便以后复现/排查。"""
    if not gid or "/" in gid or "\\" in gid or gid.startswith("."):
        return ""
    folder = os.path.join(OUTPUTS_DIR, gid)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "prompt.json")
    payload = {"generation_id": gid, "positive": positive, "negative": negative,
               "prompt": prompt, "saved_at": datetime.now().astimezone().isoformat(
                   timespec="seconds")}
    try:
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        return path
    except Exception:
        return ""


def generation_public(rec):
    """出图记录 → 前端可用的结构（图片换成可访问 URL，不暴露绝对路径）。"""
    rec = rec or {}
    data = {k: v for k, v in rec.items() if k != "images"}
    items = []
    for index, img in enumerate(rec.get("images") or [], start=1):
        items.append({
            "index": index,
            "filename": img.get("filename"),
            "subfolder": img.get("subfolder", ""),
            "type": img.get("type", "output"),
            "bytes": img.get("bytes"),
            "url": ("/api/generations/%s/image/%d" % (rec.get("generation_id"), index))
            if img.get("local") else "",
            "error": img.get("error", ""),
        })
    data["images"] = items
    return data


class Handler(BaseHTTPRequestHandler):
    server_version = "PromptWorkbench/" + __version__

    # ------------------------------------------------------------ 工具
    def _send(self, status, body, content_type="application/json; charset=utf-8", headers=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False, indent=2)
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        for key, val in (headers or {}).items():
            self.send_header(key, val)
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            # 浏览器关闭 / 刷新时客户端先断，属正常断连，不往 stderr 打堆栈。
            return
        self._log_http(status)

    def _log_http(self, status):
        try:
            path = urlparse(self.path).path
        except Exception:
            return
        if path in ("/", "/index.html", "/style.css", "/app.js") or path.startswith("/api/generations/") \
                and "/image/" in path:
            return
        if status >= 400:
            log_event("warn", "http", "%s %s → %s" % (self.command, path, status))
        elif self.command == "POST" and path not in ("/api/client-log",):
            log_event("info", "http", "%s %s" % (self.command, path))

    def _static(self, filename):
        path = os.path.join(WEB_DIR, filename)
        if not os.path.isfile(path):
            return self._send(404, {"ok": False, "message": "资源不存在：%s" % filename})
        ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype == "application/javascript":
            ctype += "; charset=utf-8"
        with open(path, "rb") as fh:
            self._send(200, fh.read(), ctype)

    def _json_body(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if not length:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    # ------------------------------------------------------------ GET
    def do_GET(self):
        route = urlparse(self.path)
        path = route.path
        query = parse_qs(route.query)

        if path in ("/", "/index.html"):
            return self._static("index.html")
        if path == "/favicon.ico":
            # 浏览器自动请求；返回空 204，避免在日志里留下无意义的 404
            return self._send(204, "")
        if path in ("/style.css", "/app.js"):
            return self._static(path.lstrip("/"))

        if path == "/api/health":
            return self._send(200, {
                "ok": True, "name": CONFIG["app"]["name"], "version": __version__,
                "base_dir": BASE_DIR,
                "history": HISTORY.stats(),
                "settings": SETTINGS.info(),
                "config": {"comfyui": COMFY_CONF, "ollama": OLLAMA_CONF},
            })

        if path == "/api/runtime":
            return self._send(200, {"ok": True, "runtime": runtime_public(),
                                    "version": __version__})

        if path == "/api/logs":
            try:
                limit = int((query.get("limit") or [100])[0])
            except ValueError:
                limit = 100
            level = (query.get("level") or [""])[0] or None
            return self._send(200, {
                "ok": True,
                "entries": LOGGER.recent(limit=limit, level=level),
                "files": LOGGER.details(),
                "last_error": LOGGER.last_error(),
            })

        if path == "/api/logs/download":
            text = LOGGER.export_text(limit=600)
            return self._send(200, text, "text/plain; charset=utf-8",
                              {"Content-Disposition":
                               'attachment; filename="workbench.log.txt"'})

        if path == "/api/backups":
            return self._send(200, {"ok": True, "backups": BACKUPS.list(),
                                    "info": BACKUPS.info()})

        if path.startswith("/api/backups/") and path.endswith("/download"):
            name = unquote(path[len("/api/backups/"):-len("/download")])
            target = BACKUPS.path_for(name)
            if target is None or not os.path.isfile(target):
                return self._send(404, {"ok": False, "message": "备份不存在：%s" % name})
            with open(target, "rb") as fh:
                blob = fh.read()
            return self._send(200, blob, "application/zip",
                              {"Content-Disposition":
                               'attachment; filename="%s"' % os.path.basename(target)})

        if path == "/api/status":
            ollama_ver = OLLAMA.version()
            model_state = OLLAMA.has_model()
            comfy = comfy_status()
            return self._send(200, {
                "ok": True,
                "version": __version__,
                "ollama": {
                    "url": OLLAMA.base_url,
                    "running": ollama_ver.get("ok", False),
                    "version": (ollama_ver.get("data") or {}).get("version", ""),
                    "target_model": OLLAMA.model,
                    "model_registered": model_state.get("has"),
                    "models": model_state.get("models", []),
                },
                "comfyui": {"url": COMFY_CONF.get("base_url", ""), "running": comfy["ok"],
                            "version": comfy.get("version", ""),
                            "queue_running": comfy.get("queue_running", 0),
                            "queue_pending": comfy.get("queue_pending", 0)},
                "vram": {
                    "auto_manage": bool(VRAM_CONF.get("auto_manage", True)),
                    "min_free_mb": VRAM_CONF.get("min_free_mb"),
                    "gpu": vram_manager.gpu_memory(),
                    "ollama_loaded": OLLAMA.loaded_models().get("models", []),
                    "last": LAST_VRAM,
                },
                "workflows_dir": WORKFLOWS_DIR,
                "workflows_dir_exists": bool(WORKFLOWS_DIR and os.path.isdir(WORKFLOWS_DIR)),
                "history": HISTORY.stats(),
                "conversations": len(HISTORY.list_conversations(1000)),
                "generations": len(HISTORY.list_generations(None, 1000)),
            })

        if path == "/api/vram":
            loaded = OLLAMA.loaded_models()
            return self._send(200, {
                "ok": True,
                "config": {k: VRAM_CONF.get(k, vram_manager.DEFAULT_CONFIG.get(k))
                           for k in vram_manager.DEFAULT_CONFIG},
                "gpu": vram_manager.gpu_memory(),
                "ollama_loaded": loaded.get("models", []),
                "last": LAST_VRAM,
            })

        if path == "/api/models":
            return self._send(200, {"ok": True, "models": LOOKUP.list_models()})

        if path == "/api/lookup":
            name = (query.get("name") or [""])[0]
            return self._send(200, LOOKUP.lookup(name))

        if path == "/api/integrity":
            return self._send(200, LOOKUP.integrity(
                checkpoints_dir=COMFY_CONF.get("models_dir") or None))

        if path == "/api/workflows":
            items = list_workflows()
            return self._send(200, {
                "ok": True,
                "dir": WORKFLOWS_DIR,
                "library_dir": LIB.lib_dir,
                "default": WB_CONF.get("default_workflow", ""),
                "counts": {"all": len(items),
                           "comfyui": sum(1 for x in items if x["source"] == "comfyui"),
                           "workbench": sum(1 for x in items if x["source"] == "workbench")},
                "workflows": items,
            })

        if path == "/api/workflow":
            name = (query.get("name") or [""])[0]
            target = workflow_path(name)
            if not target:
                return self._send(404, {"ok": False, "message": "工作流不存在：%s" % name})
            mapping = workflow_mapping(name)
            try:
                parsed = comfy_workflow.parse_workflow(target, mapping=mapping)
            except Exception as exc:
                return self._send(200, {"ok": False, "message": "工作流解析失败：%s" % exc})
            source, _ = LIB.resolve(name)
            ckpt = (parsed.get("checkpoint") or {}).get("name", "")
            match = LOOKUP.lookup(ckpt) if ckpt else {"ok": False, "reason": "no_checkpoint",
                                                     "message": "工作流里没有 CheckpointLoaderSimple"}
            ctx = CONTEXT.build(ckpt, target, mapping=mapping) if ckpt else {
                "ok": False, "reason": "no_checkpoint",
                "message": "工作流里没有 Checkpoint"}
            return self._send(200, {
                "ok": True,
                "name": os.path.basename(target),
                "source": source,
                "parsed": parsed,
                "summary": comfy_workflow.summarize(parsed),
                "candidates": comfy_workflow.mapping_candidates(parsed),
                "mapping": mapping,
                "match": match,
                "context_ok": ctx.get("ok", False),
                "context_message": ctx.get("message", ""),
                "meta": ctx.get("meta"),
            })

        if path == "/api/context":
            ckpt = (query.get("checkpoint") or [""])[0]
            wf_name = (query.get("workflow") or [""])[0]
            target = workflow_path(wf_name) if wf_name else None
            mapping = workflow_mapping(wf_name) if wf_name else {}
            if not ckpt and target:
                parsed = comfy_workflow.parse_workflow(target, mapping=mapping)
                ckpt = (parsed.get("checkpoint") or {}).get("name", "")
            return self._send(200, CONTEXT.build(ckpt, target, mapping=mapping))

        if path == "/api/settings":
            return self._send(200, {"ok": True, "settings": SETTINGS.load(),
                                    "info": SETTINGS.info(), "defaults": SETTINGS_DEFAULTS,
                                    "system": settings_system()})

        if path == "/api/generations":
            cid = (query.get("conversation_id") or [""])[0]
            try:
                limit = int((query.get("limit") or [100])[0])
            except ValueError:
                limit = 100
            records = HISTORY.list_generations(cid or None, limit)
            return self._send(200, {"ok": True, "count": len(records),
                                    "generations": [generation_public(r) for r in records]})

        if path.startswith("/api/generations/"):
            rest = unquote(path[len("/api/generations/"):])
            if "/image/" in rest:
                gid, _, index_text = rest.partition("/image/")
                rec = HISTORY.load_generation(gid)
                if not rec:
                    return self._send(404, {"ok": False, "message": "出图记录不存在：%s" % gid})
                try:
                    index = int(index_text)
                except ValueError:
                    return self._send(400, {"ok": False, "message": "图片序号不合法"})
                images = rec.get("images") or []
                if index < 1 or index > len(images) or not images[index - 1].get("local"):
                    return self._send(404, {"ok": False, "message": "图片不存在（可能没下载成功）"})
                local = os.path.abspath(images[index - 1]["local"])
                root = os.path.abspath(OUTPUTS_DIR) + os.sep
                if not local.startswith(root) or not os.path.isfile(local):
                    return self._send(403, {"ok": False, "message": "图片路径不在允许范围"})
                ctype = mimetypes.guess_type(local)[0] or "image/png"
                with open(local, "rb") as fh:
                    return self._send(200, fh.read(), ctype)
            rec = HISTORY.load_generation(rest)
            if not rec:
                return self._send(404, {"ok": False, "message": "出图记录不存在：%s" % rest})
            return self._send(200, {"ok": True, "generation": generation_public(rec)})

        if path == "/api/conversations":
            try:
                limit = int((query.get("limit") or [100])[0])
            except ValueError:
                limit = 100
            return self._send(200, {"ok": True,
                                    "conversations": HISTORY.list_conversations(limit),
                                    "stats": HISTORY.stats()})

        if path == "/api/prompts":
            cid = (query.get("conversation_id") or [""])[0]
            return self._send(200, {"ok": True, "prompts": HISTORY.list_prompts(cid or None)})

        if path.startswith("/api/conversations/"):
            rest = unquote(path[len("/api/conversations/"):])
            if rest.endswith("/export"):
                cid = rest[:-len("/export")]
                markdown = HISTORY.export_markdown(cid)
                if markdown is None:
                    return self._send(404, {"ok": False, "message": "对话不存在：%s" % cid})
                filename = "%s.md" % cid
                return self._send(200, markdown, "text/markdown; charset=utf-8",
                                  {"Content-Disposition":
                                   'attachment; filename="%s"' % filename})
            conv = HISTORY.load(rest)
            if conv is None:
                return self._send(404, {"ok": False, "message": "对话不存在：%s" % rest})
            prompts = HISTORY.list_prompts(rest)
            return self._send(200, {"ok": True, "conversation": conv, "prompts": prompts})

        return self._send(404, {"ok": False, "message": "未知路径：%s" % path})

    # ------------------------------------------------------------ POST
    def do_POST(self):
        path = urlparse(self.path).path
        body = self._json_body()

        if path == "/api/workflows/import":
            content = body.get("content")
            if isinstance(content, (dict, list)):
                content = json.dumps(content, ensure_ascii=False)
            if not content:
                return self._send(400, {"ok": False, "message": "content 不能为空"})
            result = LIB.import_text(body.get("name") or "workflow.json", content)
            if not result.get("ok"):
                return self._send(200, result)
            entry = result["entry"]
            parsed = result["parsed"]
            return self._send(200, {
                "ok": True,
                "entry": entry,
                "parsed": parsed,
                "summary": comfy_workflow.summarize(parsed),
                "candidates": comfy_workflow.mapping_candidates(parsed),
            })

        if path == "/api/workflows/mapping":
            name = body.get("name") or ""
            target = workflow_path(name)
            if not target:
                return self._send(404, {"ok": False, "message": "工作流不存在：%s" % name})
            saved = LIB.save_mapping(name, body)
            parsed = comfy_workflow.parse_workflow(target, mapping=saved)
            ctx = CONTEXT.build((parsed.get("checkpoint") or {}).get("name", ""), target,
                                mapping=saved)
            return self._send(200, {
                "ok": True,
                "mapping": saved,
                "parsed": parsed,
                "summary": comfy_workflow.summarize(parsed),
                "context_ok": ctx.get("ok", False),
                "meta": ctx.get("meta"),
            })

        if path == "/api/workflows/delete":
            name = body.get("name") or ""
            if not LIB.delete(name):
                return self._send(200, {"ok": False,
                                        "message": "只能删除工作台导入的工作流：%s" % name})
            return self._send(200, {"ok": True, "message": "已移到 workflows\\_archive"})

        if path == "/api/generate":
            code, payload = self._generate(body)
            return self._send(code, payload)

        if path.startswith("/api/generations/") and path.endswith("/retry"):
            gid = unquote(path[len("/api/generations/"):-len("/retry")])
            rec = HISTORY.load_generation(gid)
            if not rec:
                return self._send(404, {"ok": False, "message": "出图记录不存在：%s" % gid})
            params = rec.get("params") or {}
            sampler = params.get("sampler") or {}
            latent = params.get("latent") or {}
            replay = {
                "conversation_id": rec.get("conversation_id", ""),
                "workflow": rec.get("workflow", ""),
                "positive": rec.get("positive", ""),
                "negative": rec.get("negative", ""),
                "seed": sampler.get("seed"),
                "steps": sampler.get("steps"),
                "cfg": sampler.get("cfg"),
                "width": latent.get("width"),
                "height": latent.get("height"),
            }
            replay = {k: v for k, v in replay.items() if v not in (None, "")}
            if body.get("randomize"):
                replay["seed"] = "randomize"
            replay["retry_of"] = gid
            code, result = self._generate(replay)
            if result.get("ok"):
                HISTORY.update_generation(gid, {"retried_by": result.get("generation_id")})
            return self._send(200, result)

        if path == "/api/chat":
            return self._chat(body)

        if path == "/api/unload":
            result = OLLAMA.unload()
            return self._send(200, {
                "ok": result.get("ok", False),
                "message": "已请求卸载模型（keep_alive=0），服务不关" if result.get("ok")
                           else "卸载失败：%s" % result.get("error"),
            })

        if path == "/api/backups":
            try:
                made = BACKUPS.create(note=body.get("note") or "")
            except Exception as exc:
                log_event("error", "backup", "创建备份失败", error=str(exc))
                return self._send(500, {"ok": False, "message": "创建备份失败：%s" % exc})
            log_event("info", "backup", "已创建备份 %s" % made["name"],
                      files=made.get("file_count"), bytes=made.get("bytes"))
            return self._send(200, {"ok": True, "backup": made, "info": BACKUPS.info()})

        if path.startswith("/api/backups/") and path.endswith("/delete"):
            name = unquote(path[len("/api/backups/"):-len("/delete")])
            result = BACKUPS.delete(name)
            if result.get("ok"):
                log_event("warn", "backup", "备份已移入回收目录 %s" % name)
            return self._send(200 if result.get("ok") else 400, result)

        if path == "/api/client-log":
            level = str(body.get("level") or "error").lower()
            if level not in ("debug", "info", "warn", "error"):
                level = "error"
            message = str(body.get("message") or "")[:800]
            if message:
                log_event(level, "client", message,
                          detail=body.get("detail")
                          if isinstance(body.get("detail"), dict) else None,
                          url=str(body.get("url") or "")[:300])
            return self._send(200, {"ok": True})

        if path == "/api/settings":
            saved = SETTINGS.save(body)
            refresh_context()
            warnings = list(getattr(SETTINGS, "last_warnings", []) or [])
            log_event("info", "settings", "设置已保存", warnings=warnings)
            return self._send(200, {"ok": True, "settings": saved,
                                    "info": SETTINGS.info(), "warnings": warnings})

        if path == "/api/conversations":
            workflow = body.get("workflow") or ""
            target = workflow_path(workflow) if workflow else None
            checkpoint = body.get("checkpoint") or ""
            parsed = None
            if target:
                try:
                    parsed = comfy_workflow.parse_workflow(target)
                except Exception:
                    parsed = None
                checkpoint = checkpoint or (parsed.get("checkpoint") or {}).get("name", "")
            match = LOOKUP.lookup(checkpoint) if checkpoint else {}
            conv = HISTORY.create(
                title=body.get("title") or "",
                checkpoint=checkpoint,
                profile_name=(match or {}).get("profile_file", "") if (match or {}).get("ok") else "",
                workflow_id=os.path.basename(target) if target else "",
            )
            return self._send(200, {"ok": True, "conversation": conv})

        if path.startswith("/api/conversations/"):
            rest = unquote(path[len("/api/conversations/"):])
            if rest.endswith("/rename"):
                cid = rest[:-len("/rename")]
                conv = HISTORY.rename(cid, body.get("title") or "")
                if conv is None:
                    return self._send(404, {"ok": False, "message": "对话不存在：%s" % cid})
                return self._send(200, {"ok": True, "conversation": conv})
            if rest.endswith("/delete"):
                cid = rest[:-len("/delete")]
                if not HISTORY.archive(cid):
                    return self._send(404, {"ok": False, "message": "对话不存在：%s" % cid})
                return self._send(200, {"ok": True, "message": "已移到 _archive，可手动找回"})
            return self._send(404, {"ok": False, "message": "未知接口：%s" % path})

        return self._send(404, {"ok": False, "message": "未知接口：%s" % path})

    # ------------------------------------------------------------ 出图
    def _generate(self, body):
        """一次只跑一张：显存状态机不能被并发打乱。"""
        if not GENERATION_LOCK.acquire(blocking=False):
            log_event("warn", "generate", "出图请求被拒：上一张还在跑")
            return 200, {"ok": False, "reason": "busy",
                         "message": "上一张还在跑，等它结束再提交（显存只够串行）"}
        try:
            status, payload = self._generate_impl(body)
            if isinstance(payload, dict) and not payload.get("ok", False):
                message = str(payload.get("message") or "出图失败")[:500]
                level = "error" if int(status) >= 500 else "warn"
                log_event(level, "generate", "出图请求失败", http=status,
                          reason=payload.get("reason") or "")
                RUNTIME.mark_error("generate", message, http=status,
                                   reason=payload.get("reason") or "")
            return status, payload
        except Exception as exc:
            error = "服务端异常：%s: %s" % (type(exc).__name__, exc)
            log_event("error", "generate", "出图异常", error=error)
            RUNTIME.end("generate", "error", error=error, stage="异常")
            return 500, {"ok": False, "reason": "server_error", "message": error}
        finally:
            GENERATION_LOCK.release()

    def _generate_impl(self, body):
        """提交一次出图。返回 (http_status, payload)。"""
        conv_id = (body.get("conversation_id") or "").strip()
        wf_name = (body.get("workflow") or "").strip()
        if not wf_name:
            conv = HISTORY.load(conv_id) if conv_id else None
            wf_name = (conv or {}).get("workflow_id", "")
        target = workflow_path(wf_name) if wf_name else None
        if not target:
            return 400, {"ok": False, "reason": "no_workflow",
                         "message": "没有可用的工作流：请先用 suyuexisdxl.json 这类完整工作流建一段对话，"
                                    "或指定 workflow"}

        mapping = workflow_mapping(wf_name)
        try:
            parsed = comfy_workflow.parse_workflow(target, mapping=mapping)
        except Exception as exc:
            return 200, {"ok": False, "reason": "parse_failed",
                         "message": "工作流解析失败：%s" % exc}

        pos_ids = (parsed.get("positive") or {}).get("node_ids") or []
        neg_ids = (parsed.get("negative") or {}).get("node_ids") or []
        positive = (body.get("positive") or (parsed.get("positive") or {}).get("text") or "").strip()
        negative = (body.get("negative") or (parsed.get("negative") or {}).get("text") or "").strip()
        if not positive:
            return 400, {"ok": False, "reason": "no_positive", "message": "正向提示词为空"}
        if not pos_ids or not neg_ids:
            return 400, {"ok": False, "reason": "no_nodes",
                         "message": "正负节点未判定：请在工作流面板用人工映射指定正向/负向节点"}

        try:
            source = comfy_workflow.load_json(target)
            fmt = comfy_workflow.detect_format(source)
        except Exception as exc:
            return 200, {"ok": False, "reason": "load_failed", "message": "读取工作流失败：%s" % exc}

        try:
            object_info = COMFY.object_info()
        except Exception as exc:
            return 200, {"ok": False, "reason": "comfy_unavailable",
                         "message": "取不到 ComfyUI 的 object_info：%s" % exc,
                         "hint": "先打开绘世启动器把 ComfyUI 跑起来（API 端口 8188）"}

        warnings = []
        try:
            if fmt == "ui":
                prompt, warnings = comfy_api.convert_ui_to_api(source, object_info)
            else:
                prompt = comfy_api.copy_prompt(source)
        except comfy_api.ConversionError as exc:
            return 200, {"ok": False, "reason": "convert_failed",
                         "message": "UI → API 转换失败：%s" % exc}

        changed = comfy_api.set_text_inputs(prompt, pos_ids, positive)
        changed += comfy_api.set_text_inputs(prompt, neg_ids, negative)
        if not changed:
            return 200, {"ok": False, "reason": "text_not_written",
                         "message": "提示词没写进节点：正/负节点可能不是 CLIPTextEncode"}

        overrides = {}
        for key in ("seed", "steps", "cfg", "width", "height", "batch"):
            value = body.get(key)
            if value not in (None, ""):
                overrides[key] = value
        if str(body.get("seed")) == "randomize":
            overrides["seed"] = random.getrandbits(63)
        sampler_ids = [s.get("node_id") for s in (parsed.get("samplers") or []) if s.get("node_id")]
        applied = comfy_api.apply_overrides(prompt, sampler_ids, overrides)
        if overrides and not applied:
            warnings.append("参数覆盖没生效：工作流里没有对应的采样器/空 Latent 节点")

        params = comfy_api.params_from_prompt(prompt, sampler_ids, pos_ids, neg_ids)
        checkpoint = (parsed.get("checkpoint") or {}).get("name") or comfy_api.checkpoint_of(prompt)
        match = LOOKUP.lookup(checkpoint)
        record = HISTORY.save_generation(conv_id, {
            "workflow": os.path.basename(target),
            "checkpoint": checkpoint,
            "profile": (match or {}).get("profile_file", ""),
            "positive": positive,
            "negative": negative,
            "params": params,
            "warnings": warnings,
            "workflow_format": fmt,
            "prompt_id": "",
            "status": "running",
            "attempts": 0,
            "retry_of": body.get("retry_of") or "",
        })
        gid = record["generation_id"]

        RUNTIME.begin("generate", conversation_id=conv_id, generation_id=gid,
                      workflow=os.path.basename(target), stage="显存准备")
        log_event("info", "generate", "开始出图 %s" % gid,
                  workflow=os.path.basename(target), positive_chars=len(positive))

        # 阶段 6：先把显存让给 ComfyUI（Ollama 检测 → 存上下文 → 卸载 → 显存检测 → ComfyUI 检测）
        vram = vram_safe("vram_start", VRAM.start, conv_id, auto=body.get("manage_vram"))
        if any(s.get("name") == "vram_start_error" for s in vram.get("steps") or []):
            vram["fatal"] = True
        if vram.get("fatal"):
            last = keep_vram_summary(vram_safe("vram_abort", VRAM.abort, "显存准备失败"))
            error = "显存准备失败：%s" % ("；".join(vram.get("errors") or []) or "未知原因")
            HISTORY.update_generation(gid, {"status": "error", "error": error,
                                            "vram": last})
            RUNTIME.end("generate", "error", error=error, stage="显存准备失败")
            log_event("error", "generate", "显存准备失败 %s" % gid, error=error)
            return 200, {"ok": False, "reason": "vram_prepare_failed", "generation_id": gid,
                         "message": error, "vram": last, "retryable": True}

        # 提交（连接失败时先重试一次，节点校验失败不重试）
        RUNTIME.update("generate", stage="提交 ComfyUI")
        attempts = 0
        result = {"ok": False, "error": "未提交"}
        for attempt in range(2):
            attempts = attempt + 1
            result = COMFY.queue_prompt(prompt)
            if result.get("ok") or "连不上" not in str(result.get("error")):
                break
            time.sleep(1.5)
        if not result.get("ok"):
            last = keep_vram_summary(vram_safe("vram_abort", VRAM.abort, "提交 ComfyUI 失败"))
            HISTORY.update_generation(gid, {"status": "error", "error": result.get("error", ""),
                                            "attempts": attempts, "vram": last})
            RUNTIME.end("generate", "error", error=result.get("error", ""),
                        stage="提交失败")
            log_event("error", "generate", "提交 ComfyUI 失败 %s" % gid,
                      error=result.get("error", ""))
            return 200, {"ok": False, "reason": "submit_failed", "generation_id": gid,
                         "message": "提交 ComfyUI 失败：%s" % result.get("error"),
                         "vram": last, "retryable": True}

        pid = result["prompt_id"]
        HISTORY.update_generation(gid, {"prompt_id": pid, "attempts": attempts})
        _save_prompt_snapshot(gid, prompt, positive, negative)
        RUNTIME.update("generate", stage="等待 ComfyUI 执行", prompt_id=pid)

        timeout = int(body.get("timeout") or COMFY_TIMEOUT)
        started = time.time()
        status, data = COMFY.wait(pid, timeout=timeout, interval=1.0)
        duration = round(time.time() - started, 1)
        if status != "done":
            error = (data or {}).get("error") or "出图失败"
            VRAM.after_comfy()
            last = keep_vram_summary(vram_safe("vram_abort", VRAM.abort, "ComfyUI 执行失败"))
            HISTORY.update_generation(gid, {"status": "error", "error": error,
                                            "duration_sec": duration, "vram": last})
            RUNTIME.end("generate", "error", error=error, stage="ComfyUI 执行失败",
                        duration_sec=duration)
            log_event("error", "generate", "ComfyUI 执行失败 %s" % gid, error=error,
                      duration_sec=duration)
            return 200, {"ok": False, "reason": status, "generation_id": gid, "prompt_id": pid,
                         "message": error, "duration_sec": duration, "vram": last,
                         "retryable": True}

        images = comfy_api.images_from_history(data.get("entry"))
        if not images:
            VRAM.after_comfy()
            last = keep_vram_summary(vram_safe("vram_abort", VRAM.abort, "没有图片输出"))
            HISTORY.update_generation(gid, {"status": "error", "error": "执行完成但没有图片输出",
                                            "duration_sec": duration, "vram": last})
            RUNTIME.end("generate", "error", error="执行完成但没有图片输出",
                        stage="没有图片输出", duration_sec=duration)
            log_event("error", "generate", "没有图片输出 %s" % gid)
            return 200, {"ok": False, "reason": "no_images", "generation_id": gid, "prompt_id": pid,
                         "message": "执行完成，但工作流里没有 SaveImage 输出", "vram": last}

        RUNTIME.update("generate", stage="下载图片")
        saved = comfy_api.save_images(COMFY, gid, images, OUTPUTS_DIR)
        missing = [s for s in saved if not s.get("local")]
        # 阶段 6：释放 ComfyUI 模型/缓存 → 重新加载 Ollama → 核对上下文可续聊
        RUNTIME.update("generate", stage="恢复显存与上下文")
        VRAM.after_comfy()
        # 设置页的“出图后自动恢复 Ollama”即时生效；关闭时只恢复上下文不重载模型
        try:
            VRAM.cfg["reload_ollama"] = bool(
                SETTINGS.load().get("application", {}).get("auto_restore_ollama", True))
        except Exception:
            pass
        last = keep_vram_summary(vram_safe("vram_restore", VRAM.restore))
        record = HISTORY.update_generation(gid, {
            "status": "done", "images": saved, "duration_sec": duration,
            "prompt_id": pid, "attempts": attempts,
            "error": "" if not missing else "有 %d 张图没下载成功" % len(missing),
            "vram": last,
        })
        if missing:
            RUNTIME.end("generate", "error", error="有 %d 张图没下载成功" % len(missing),
                        stage="图片下载不完整", duration_sec=duration)
            log_event("warn", "generate", "图片下载不完整 %s" % gid,
                      missing=len(missing), duration_sec=duration)
        else:
            RUNTIME.end("generate", "ok", stage="完成", duration_sec=duration,
                        images=len(saved))
            log_event("info", "generate", "出图完成 %s" % gid, duration_sec=duration,
                      images=len(saved), vram_after=(last.get("vram_after") or {}).get("used_mb"))
        return 200, {"ok": True, "generation_id": gid, "prompt_id": pid,
                     "generation": generation_public(record),
                     "params": params, "duration_sec": duration, "attempts": attempts,
                     "warnings": warnings, "vram": last}

    # ------------------------------------------------------------ 对话
    def _chat(self, body):
        message = (body.get("message") or "").strip()
        cid = body.get("conversation_id") or ""
        regenerate = bool(body.get("regenerate"))
        legacy = body.get("messages") or []

        if not message and legacy:
            for item in legacy:
                if item.get("role") == "user" and (item.get("content") or "").strip():
                    message = item["content"].strip()

        if not message and not regenerate:
            return self._send(400, {"ok": False, "message": "message 不能为空"})

        auto_save = bool((SETTINGS.load().get("application") or {}).get("auto_save_history", True))

        conv = HISTORY.load(cid) if cid else None
        if cid and conv is None:
            return self._send(404, {"ok": False, "message": "对话不存在：%s" % cid})

        wf_name = body.get("workflow") or (conv or {}).get("workflow_id", "")
        target = workflow_path(wf_name) if wf_name else None
        mapping = workflow_mapping(wf_name) if wf_name else {}
        checkpoint = body.get("checkpoint") or (conv or {}).get("checkpoint", "")
        if target:
            try:
                parsed = comfy_workflow.parse_workflow(target, mapping=mapping)
            except Exception as exc:
                return self._send(200, {"ok": False, "message": "工作流解析失败：%s" % exc})
            checkpoint = checkpoint or (parsed.get("checkpoint") or {}).get("name", "")

        if not checkpoint:
            return self._send(200, {
                "ok": False, "reason": "no_checkpoint",
                "message": "无法确定当前 checkpoint：请选择包含 CheckpointLoaderSimple 的工作流，或直接指定模型名",
            })

        ctx = CONTEXT.build(checkpoint, target, mapping=mapping)
        if not ctx.get("ok"):
            return self._send(200, {
                "ok": False, "reason": ctx.get("reason"), "message": ctx.get("message"),
                "hint": ctx.get("hint", ""),
            })

        # 新建对话（首次发言自动建）
        if conv is None:
            match = ctx.get("meta") or {}
            conv = HISTORY.create(title=(message[:40] if message else ""),
                                  checkpoint=checkpoint,
                                  profile_name=match.get("profile_file", ""),
                                  workflow_id=os.path.basename(target) if target else "")
            cid = conv["conversation_id"]
        else:
            # 换工作流时同步元信息，历史不清空
            changed = (conv.get("checkpoint") != checkpoint) or \
                      (target and conv.get("workflow_id") != os.path.basename(target))
            if changed:
                conv["checkpoint"] = checkpoint
                if target:
                    conv["workflow_id"] = os.path.basename(target)
                conv["profile_name"] = (ctx.get("meta") or {}).get("profile_file", "")
                HISTORY.save(conv)

        # 重新生成：去掉最后一条回复，沿用同一条用户消息
        if regenerate:
            if not HISTORY.load(cid)["messages"]:
                return self._send(200, {"ok": False, "message": "这段对话还没有可重试的内容"})
            HISTORY.drop_last_assistant(cid)
            history = HISTORY.history_for_ollama(cid, history_limit())
            if not history or history[-1]["role"] != "user":
                return self._send(200, {"ok": False, "message": "最后一条不是用户消息，无法重试"})
            message = history[-1]["content"]
        else:
            if auto_save:
                HISTORY.append_message(cid, "user", message)
                history = HISTORY.history_for_ollama(cid, history_limit())
            else:
                history = HISTORY.history_for_ollama(cid, history_limit())
                history = history + [{"role": "user", "content": message}]

        payload = [{"role": "system", "content": ctx["system"]}] + history
        RUNTIME.begin("chat", conversation_id=cid, message_chars=len(message),
                      stage="等待 Ollama 生成")
        log_event("info", "chat", "对话请求", conversation_id=cid,
                  message_chars=len(message), history_messages=len(history),
                  workflow=os.path.basename(target) if target else "")
        result = OLLAMA.chat(payload)
        if not result.get("ok"):
            RUNTIME.end("chat", "error", error=result.get("error", ""),
                        stage="Ollama 调用失败")
            log_event("error", "chat", "Ollama 调用失败", error=result.get("error", ""))
            return self._send(200, {
                "ok": False, "reason": "ollama_error",
                "message": "Ollama 调用失败：%s" % result.get("error"),
                "hint": "确认 Ollama 桌面版 App 在运行，且模型 %s 已注册" % OLLAMA.model,
                "conversation_id": cid,
            })

        content = result.get("content", "")
        guard = output_guard.analyse(content)
        attempts = 1
        best = (content, guard, result)

        if not guard["ok"]:
            # 逐次收紧，最多再试两次；宁可要短一点的完整答案，也不要接龙
            for options in ({"temperature": 0.2, "repeat_penalty": 1.4, "num_predict": 900},
                            {"temperature": 0.1, "repeat_penalty": 1.5, "num_predict": 700}):
                retry_history = [dict(m) for m in history]
                for m in reversed(retry_history):
                    if m["role"] == "user":
                        m["content"] = m["content"] + output_guard.RETRY_NOTE
                        break
                RUNTIME.update("chat", stage="输出失控，自动重试 %d/2" % attempts)
                retry = OLLAMA.chat([payload[0]] + retry_history, options=options)
                if not retry.get("ok"):
                    continue
                retry_text = retry.get("content", "")
                retry_guard = output_guard.analyse(retry_text)
                attempts += 1
                if retry_guard["ok"] or len(retry_text) < len(best[0]):
                    best = (retry_text, retry_guard, retry)
                if retry_guard["ok"]:
                    break
        content, guard, result = best

        parts = prompt_extract.extract(content)
        meta = {
            "profile_file": (ctx.get("meta") or {}).get("profile_file", ""),
            "injected_chars": (ctx.get("meta") or {}).get("injected_chars"),
            "attempts": attempts,
            "guard_ok": guard["ok"],
            "prompt_tokens": result.get("prompt_eval_count"),
            "output_tokens": result.get("eval_count"),
        }

        prompt_record = None
        if auto_save:
            if parts["positive"] or parts["negative"]:
                prompt_record = HISTORY.save_prompt(
                    cid, parts["positive"], parts["negative"], parts["settings"],
                    checkpoint=checkpoint, profile=meta["profile_file"])
            HISTORY.append_message(cid, "assistant", content, meta=meta,
                                   prompt_id=(prompt_record or {}).get("prompt_id"))

        conv = HISTORY.load(cid)
        RUNTIME.end("chat", "ok", stage="完成" if guard["ok"] else "完成（输出被标记可能失控）",
                    output_chars=len(content), attempts=attempts,
                    prompt_tokens=result.get("prompt_eval_count"))
        log_event("info", "chat", "对话完成", conversation_id=cid,
                  output_chars=len(content), attempts=attempts,
                  guard_ok=guard["ok"], prompt_tokens=result.get("prompt_eval_count"))

        return self._send(200, {
            "ok": True,
            "content": content,
            "parts": parts,
            "conversation_id": cid,
            "conversation": conv,
            "prompt": prompt_record,
            "meta": ctx.get("meta"),
            "attempts": attempts,
            "guard": guard,
            "usage": {"prompt_tokens": result.get("prompt_eval_count"),
                      "output_tokens": result.get("eval_count")},
            "auto_saved": auto_save,
        })

    def log_message(self, fmt, *args):
        pass


SETTINGS_DEFAULTS = {
    "application": {"theme": "dark", "auto_save_history": True,
                    "auto_restore_ollama": True, "confirm_delete": True},
    "chat": {"history_max_messages": 20, "system_prompt_variant": "精简版"},
}


def browser_enabled(argv=None, environ=None):
    """默认不弹浏览器，避免测试/后台启动时打扰。

    只有显式 --open-browser 或 WORKBENCH_OPEN_BROWSER=1 才打开；
    --no-browser 优先级最高，便于脚本强制关闭。
    """
    argv = sys.argv[1:] if argv is None else argv
    environ = os.environ if environ is None else environ
    if "--no-browser" in argv:
        return False
    return "--open-browser" in argv or str(environ.get("WORKBENCH_OPEN_BROWSER", "")) == "1"


def open_browser(url):
    """用系统默认浏览器打开工作台；失败只记日志，不影响服务。"""
    try:
        if os.name == "nt":
            os.startfile(url)  # type: ignore[attr-defined]
        else:
            webbrowser.open(url, new=2)
        log_event("info", "server", "已请求打开浏览器", url=url)
    except Exception as exc:
        log_event("warn", "server", "打开浏览器失败", url=url, error=str(exc))
        print("[warn] 打开浏览器失败：%s；请手动打开 %s" % (exc, url))


def main():
    host = CONFIG["app"]["host"]
    port = int(CONFIG["app"]["port"])
    server = ThreadingHTTPServer((host, port), Handler)
    url = "http://%s:%d" % (host, port)
    log_event("info", "server", "工作台启动", version=__version__,
              url=url, pid=os.getpid())
    print("=" * 56)
    print(" %s  %s" % (CONFIG["app"]["name"], __version__))
    print(" 已登记模型：%d 个；工作流目录：%s" % (len(LOOKUP.registered), WORKFLOWS_DIR or "(未配置)"))
    print(" 历史目录：%s" % os.path.join(BASE_DIR, "history"))
    print(" Ollama：%s（%s）" % (OLLAMA.base_url, OLLAMA.model))
    print(" 打开：%s" % url)
    if browser_enabled():
        timer = threading.Timer(0.8, open_browser, args=(url,))
        timer.daemon = True
        timer.start()
        print(" 已安排自动打开默认浏览器；不需要请加 --no-browser")
    print(" 退出：Ctrl+C")
    print("=" * 56)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")
    finally:
        server.server_close()
        log_event("info", "server", "工作台已停止")


if __name__ == "__main__":
    main()
