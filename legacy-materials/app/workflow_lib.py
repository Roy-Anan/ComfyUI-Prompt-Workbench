# -*- coding: utf-8 -*-
r"""阶段 4：工作流库。

职责：
- 导入 UI Workflow JSON / API Prompt JSON，存进工作台自己的 `workflows\` 目录（不改 ComfyUI 原目录）；
- 同时列出 ComfyUI 自带工作流（只读）与工作台导入的（可人工映射）；
- 人工节点映射存 `workflows\mappings\<名字>.json`，供解析器覆盖自动判定结果；
- 所有名字都做 basename + 非法字符清洗，`..\` 之类无法落地。
"""

from __future__ import annotations

import io
import json
import os
import re
import time
from datetime import datetime

from app import comfy_workflow

INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _atomic_write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with io.open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


class WorkflowLibrary:
    def __init__(self, base_dir, comfy_dir=""):
        self.base_dir = os.path.abspath(base_dir)
        self.comfy_dir = comfy_dir or ""
        self.lib_dir = os.path.join(self.base_dir, "workflows")
        self.map_dir = os.path.join(self.lib_dir, "mappings")
        self.archive_dir = os.path.join(self.lib_dir, "_archive")
        self.index_path = os.path.join(self.lib_dir, "workflows_index.json")
        self.index_name = os.path.basename(self.index_path).lower()
        for path in (self.lib_dir, self.map_dir):
            os.makedirs(path, exist_ok=True)

    def _is_index(self, name):
        return self.safe_name(name).lower() == self.index_name

    # ---------------------------------------------------------------- 名字
    @staticmethod
    def safe_name(name):
        base = os.path.basename(str(name or "").replace("\\", "/").strip())
        base = INVALID_CHARS.sub("_", base)
        if not base:
            return ""
        if not base.lower().endswith(".json"):
            base += ".json"
        if base in ("..json", ".json"):
            return ""
        return base

    @staticmethod
    def _strict(name):
        """拒绝带路径分隔符或 .. 的输入（防穿越），而不是悄悄 basename 化。"""
        raw = str(name or "").strip()
        if "/" in raw or "\\" in raw or ".." in raw:
            return False
        return bool(raw)

    def resolve(self, name):
        """返回 (source, path)；工作台优先，其次 ComfyUI 目录。"""
        if not self._strict(name):
            return None, None
        base = self.safe_name(name)
        if not base:
            return None, None
        if self._is_index(base):
            return None, None
        local = os.path.join(self.lib_dir, base)
        if os.path.isfile(local):
            return "workbench", local
        if self.comfy_dir:
            external = os.path.join(self.comfy_dir, base)
            if os.path.isfile(external):
                return "comfyui", external
        return None, None

    # ---------------------------------------------------------------- 映射
    def _map_path(self, name):
        base = self.safe_name(name)
        if not base:
            return None
        return os.path.join(self.map_dir, base[:-5] + ".mapping.json")

    def load_mapping(self, name):
        path = self._map_path(name)
        if not path or not os.path.isfile(path):
            return {}
        try:
            with io.open(path, encoding="utf-8-sig") as fh:
                data = json.load(fh)
        except Exception:
            return {}
        allowed = ("positive_node", "negative_node", "sampler_node")
        return {k: (str(data[k]) if data.get(k) not in (None, "") else None)
                for k in allowed if k in data}

    def save_mapping(self, name, mapping):
        if not self._strict(name):
            return None
        path = self._map_path(name)
        if not path:
            return None
        current = self.load_mapping(name)
        for key in ("positive_node", "negative_node", "sampler_node"):
            if key in (mapping or {}):
                value = mapping.get(key)
                current[key] = str(value) if value not in (None, "") else None
        current["name"] = self.safe_name(name)
        current["updated_at"] = _now()
        _atomic_write(path, json.dumps(current, ensure_ascii=False, indent=2))
        return current

    # ---------------------------------------------------------------- 导入
    def import_text(self, name, text):
        """把用户上传的 JSON 文本存进工作台库。返回 {ok, entry, parsed} 或 {ok:False, message}。"""
        try:
            data = json.loads(text)
        except Exception as exc:
            return {"ok": False, "message": "JSON 解析失败：%s" % exc}
        try:
            fmt = comfy_workflow.detect_format(data)
        except ValueError as exc:
            return {"ok": False, "message": str(exc)}

        base = self.safe_name(name or "workflow.json")
        if not base:
            return {"ok": False, "message": "文件名不合法：%s" % name}
        stem, ext = os.path.splitext(base)
        final = base
        counter = 2
        while os.path.exists(os.path.join(self.lib_dir, final)) or \
                (self.comfy_dir and os.path.exists(os.path.join(self.comfy_dir, final))):
            final = "%s-%d%s" % (stem, counter, ext)
            counter += 1

        path = os.path.join(self.lib_dir, final)
        _atomic_write(path, json.dumps(data, ensure_ascii=False, indent=2))

        try:
            parsed = comfy_workflow.parse_workflow(path, mapping=self.load_mapping(final))
        except Exception as exc:
            return {"ok": False, "message": "已保存但解析失败：%s" % exc, "name": final}

        entry = {
            "name": final,
            "original_name": os.path.basename(str(name or "")),
            "source": "workbench",
            "format": fmt,
            "node_count": len(parsed.get("nodes") or []),
            "checkpoint": (parsed.get("checkpoint") or {}).get("name", ""),
            "imported_at": _now(),
            "size": os.path.getsize(path),
        }
        self._update_index(entry)
        return {"ok": True, "entry": entry, "parsed": parsed}

    def _read_index(self):
        try:
            with io.open(self.index_path, encoding="utf-8-sig") as fh:
                data = json.load(fh)
            if isinstance(data.get("workflows"), dict):
                return data
        except Exception:
            pass
        return {"workflows": {}, "updated_at": ""}

    def _update_index(self, entry):
        index = self._read_index()
        index["workflows"][entry["name"]] = entry
        index["updated_at"] = _now()
        _atomic_write(self.index_path, json.dumps(index, ensure_ascii=False, indent=2))

    # ---------------------------------------------------------------- 列表
    def _brief(self, name, source, path):
        item = {"name": name, "source": source, "path": path,
                "size": os.path.getsize(path),
                "modified": datetime.fromtimestamp(os.path.getmtime(path)).astimezone()
                .isoformat(timespec="seconds"),
                "has_mapping": bool(self.load_mapping(name))}
        try:
            parsed = comfy_workflow.parse_workflow(path, mapping=self.load_mapping(name))
            item.update({
                "ok": True,
                "format": parsed.get("format"),
                "node_count": len(parsed.get("nodes") or []),
                "checkpoint": (parsed.get("checkpoint") or {}).get("name", ""),
                "positive_nodes": (parsed.get("positive") or {}).get("node_ids", []),
                "negative_nodes": (parsed.get("negative") or {}).get("node_ids", []),
            })
        except Exception as exc:
            item.update({"ok": False, "error": "%s" % exc})
        return item

    def list_all(self):
        items = []
        names = set()
        if self.comfy_dir and os.path.isdir(self.comfy_dir):
            for fn in os.listdir(self.comfy_dir):
                if fn.lower().endswith(".json") and fn.lower() != self.index_name \
                        and os.path.isfile(os.path.join(self.comfy_dir, fn)):
                    names.add(fn)
        if os.path.isdir(self.lib_dir):
            for fn in os.listdir(self.lib_dir):
                if fn.lower().endswith(".json") and fn.lower() != self.index_name \
                        and os.path.isfile(os.path.join(self.lib_dir, fn)):
                    names.add(fn)
        for fn in sorted(names):
            source, path = self.resolve(fn)
            if not path:
                continue
            items.append(self._brief(fn, source, path))
        return items

    def delete(self, name):
        """只允许删工作台导入的；移到 workflows\\_archive。"""
        if not self._strict(name):
            return False
        base = self.safe_name(name)
        if not base or self._is_index(base):
            return False
        local = os.path.join(self.lib_dir, base)
        if not local or not os.path.isfile(local):
            return False
        os.makedirs(self.archive_dir, exist_ok=True)
        target = os.path.join(self.archive_dir, "%s.deleted-%s.json"
                              % (os.path.splitext(base)[0], int(time.time())))
        os.replace(local, target)
        map_path = self._map_path(base)
        if map_path and os.path.isfile(map_path):
            os.remove(map_path)
        index = self._read_index()
        index["workflows"].pop(base, None)
        index["updated_at"] = _now()
        _atomic_write(self.index_path, json.dumps(index, ensure_ascii=False, indent=2))
        return True
