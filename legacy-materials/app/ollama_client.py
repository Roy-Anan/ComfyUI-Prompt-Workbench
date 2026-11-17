# -*- coding: utf-8 -*-
"""Ollama 客户端（标准库，无第三方依赖）。

注意：必须连 Ollama 桌面版 App 起的服务（默认 http://127.0.0.1:11434）。
模型库在 D:\\AI\\MODELS，只有 App 认这个目录；自己起 ollama serve 会看到空库。
"""

import json
import urllib.error
import urllib.request


class OllamaClient:
    def __init__(self, base_url="http://127.0.0.1:11434", model="comfyui-prompt:v1",
                 keep_alive="30m", timeout=180, options=None):
        self.base_url = (base_url or "http://127.0.0.1:11434").rstrip("/")
        self.model = model or "comfyui-prompt:v1"
        self.keep_alive = keep_alive
        self.timeout = timeout
        self.options = dict(options or {})

    # ---------------------------------------------------------------- 底层
    def _call(self, path, payload=None, timeout=None):
        url = self.base_url + path
        data = None
        headers = {}
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers,
                                     method="POST" if data else "GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
                return {"ok": True, "data": json.loads(resp.read().decode("utf-8"))}
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", "replace")
            except Exception:
                pass
            return {"ok": False, "error": "HTTP %s: %s" % (exc.code, body[:400])}
        except urllib.error.URLError as exc:
            return {"ok": False, "error": "连不上 Ollama（%s）：%s" % (self.base_url, exc.reason)}
        except Exception as exc:
            return {"ok": False, "error": "%s: %s" % (type(exc).__name__, exc)}

    # ---------------------------------------------------------------- 接口
    def version(self):
        return self._call("/api/version", timeout=5)

    def tags(self):
        return self._call("/api/tags", timeout=8)

    def has_model(self, model=None):
        result = self.tags()
        if not result["ok"]:
            return {"ok": False, "error": result["error"]}
        names = [m.get("name") for m in result["data"].get("models", [])]
        target = model or self.model
        return {"ok": True, "models": names, "has": target in names, "target": target}

    def ps(self):
        return self._call("/api/ps", timeout=8)

    def loaded_models(self):
        """当前驻留在显存/内存里的模型（含 size_vram）。"""
        result = self.ps()
        if not result.get("ok"):
            return {"ok": False, "error": result.get("error"), "models": []}
        items = []
        for item in (result["data"] or {}).get("models") or []:
            items.append({"name": item.get("name"),
                          "size": item.get("size"),
                          "size_vram": item.get("size_vram"),
                          "expires_at": item.get("expires_at")})
        return {"ok": True, "models": items}

    def preload(self, model=None, keep_alive=None):
        """把模型重新装回显存（空 prompt 的 /api/generate 就是纯加载）。"""
        payload = {"model": model or self.model, "prompt": "", "stream": False,
                   "keep_alive": str(keep_alive or self.keep_alive)}
        result = self._call("/api/generate", payload=payload, timeout=180)
        return result

    def chat(self, messages, options=None):
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "keep_alive": self.keep_alive,
        }
        merged = dict(self.options)
        if options:
            merged.update(options)
        if merged:
            payload["options"] = merged
        result = self._call("/api/chat", payload=payload, timeout=max(self.timeout, 300))
        if not result["ok"]:
            return result
        data = result["data"]
        content = ((data.get("message") or {}).get("content") or "").strip()
        return {
            "ok": True,
            "content": content,
            "eval_count": data.get("eval_count"),
            "prompt_eval_count": data.get("prompt_eval_count"),
            "total_duration": data.get("total_duration"),
        }

    def unload(self, model=None):
        """只卸载模型（keep_alive=0），不关服务。"""
        payload = {"model": model or self.model, "keep_alive": 0}
        result = self._call("/api/generate", payload=payload, timeout=30)
        return result
