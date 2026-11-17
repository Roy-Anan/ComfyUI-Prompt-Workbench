# -*- coding: utf-8 -*-
"""Ollama 连通性探针：版本 / 模型列表 / 已加载模型。"""

import json
import urllib.request

for path in ("/api/version", "/api/tags", "/api/ps"):
    url = "http://127.0.0.1:11434" + path
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if path == "/api/tags":
            print("tags:", [m.get("name") for m in data.get("models", [])])
        else:
            print(path, "->", json.dumps(data, ensure_ascii=False)[:300])
    except Exception as exc:
        print(path, "-> FAIL", type(exc).__name__, exc)
