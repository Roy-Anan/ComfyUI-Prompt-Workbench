# -*- coding: utf-8 -*-
"""settings\app_settings.json 的读写。

计划书要求：保存配置前备份旧配置；更新程序不覆盖用户数据。
old 文件先复制成 app_settings.bak.json，再原子替换。
"""

from __future__ import annotations

import json
import os
import shutil
import threading
from datetime import datetime

DEFAULTS = {
    "application": {
        "theme": "dark",
        "auto_save_history": True,
        "auto_restore_ollama": True,
        "confirm_delete": True,
    },
    "chat": {
        "history_max_messages": 20,
        "system_prompt_variant": "精简版",
    },
    "ollama": {
        "base_url": "http://127.0.0.1:11434",
        "model": "comfyui-prompt:v1",
    },
    "comfyui": {
        "base_url": "http://127.0.0.1:8188",
    },
}


CHAT_VARIANTS = ("精简版", "全量版")


def validate_patch(patch):
    """把前端提交的设置收窄到安全范围，返回 (clean, warnings)。

    只认白名单键；数字做上下限；布尔只接受真布尔；枚举只接受已知值。
    """
    clean, warnings = {}, []
    if not isinstance(patch, dict):
        return clean, ["设置内容不是对象，已忽略"]
    for section, values in patch.items():
        if section not in DEFAULTS or not isinstance(DEFAULTS[section], dict):
            continue
        if not isinstance(values, dict):
            continue
        for key, val in values.items():
            if key not in DEFAULTS[section]:
                continue
            default = DEFAULTS[section][key]
            if isinstance(default, bool):
                if isinstance(val, bool):
                    clean.setdefault(section, {})[key] = val
                else:
                    warnings.append("%s.%s 需要 true/false，已忽略" % (section, key))
            elif isinstance(default, int):
                try:
                    number = int(val)
                except (TypeError, ValueError):
                    warnings.append("%s.%s 需要整数，已忽略" % (section, key))
                    continue
                if key == "history_max_messages":
                    clamped = max(2, min(60, number))
                    if clamped != number:
                        warnings.append("history_max_messages 已收窄到 %d" % clamped)
                    clean.setdefault(section, {})[key] = clamped
                else:
                    clean.setdefault(section, {})[key] = number
            elif isinstance(default, str):
                text = str(val or "").strip()
                if key == "system_prompt_variant":
                    if text not in CHAT_VARIANTS:
                        warnings.append("system_prompt_variant 只支持 精简版 / 全量版，已忽略")
                        continue
                if key == "theme":
                    text = "dark"
                if key == "base_url":
                    if not (text.startswith("http://") or text.startswith("https://")):
                        warnings.append("%s.%s 需要 http(s) 地址，已忽略" % (section, key))
                        continue
                clean.setdefault(section, {})[key] = text
            else:
                clean.setdefault(section, {})[key] = val
    return clean, warnings


def _merge(defaults, loaded):
    out = {}
    for key, val in defaults.items():
        out[key] = dict(val) if isinstance(val, dict) else val
        if isinstance(val, dict) and isinstance(loaded.get(key), dict):
            for sub_key, sub_val in val.items():
                out[key].setdefault(sub_key, sub_val)
                if sub_key in loaded[key]:
                    out[key][sub_key] = loaded[key][sub_key]
    for key, val in loaded.items():
        out.setdefault(key, val)
    return out


class SettingsStore:
    def __init__(self, base_dir):
        self.base_dir = os.path.abspath(base_dir)
        self.dir = os.path.join(self.base_dir, "settings")
        self.path = os.path.join(self.dir, "app_settings.json")
        self.backup_path = os.path.join(self.dir, "app_settings.bak.json")
        os.makedirs(self.dir, exist_ok=True)
        self._lock = threading.RLock()
        self.last_warnings = []

    def load(self):
        with self._lock:
            if not os.path.isfile(self.path):
                self._write(DEFAULTS, backup=False)
                return json.loads(json.dumps(DEFAULTS))
            try:
                with open(self.path, encoding="utf-8-sig") as fh:
                    loaded = json.load(fh)
            except Exception:
                # 坏文件不丢：重命名留证，再回默认值
                stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                try:
                    shutil.move(self.path, self.path + ".corrupt-" + stamp)
                except Exception:
                    pass
                return json.loads(json.dumps(DEFAULTS))
            return _merge(DEFAULTS, loaded)

    def _write(self, payload, backup=True):
        if backup and os.path.isfile(self.path):
            try:
                shutil.copy2(self.path, self.backup_path)
            except Exception:
                pass
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.path)

    def save(self, patch):
        """只接受白名单键，未知键忽略，避免前端写坏配置。"""
        clean, warnings = validate_patch(patch)
        with self._lock:
            current = self.load()
            for section, values in clean.items():
                for key, val in values.items():
                    current[section][key] = val
            self._write(current, backup=True)
            self.last_warnings = warnings
            return current

    def info(self):
        return {"path": self.path, "backup": self.backup_path,
                "exists": os.path.isfile(self.path),
                "backup_exists": os.path.isfile(self.backup_path),
                "dir": self.dir}
