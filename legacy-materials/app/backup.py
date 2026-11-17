# -*- coding: utf-8 -*-
r"""阶段 7：本地数据备份。

备份内容（只带用户数据，不带程序包与出图原图）：
    history\      对话 / 提示词 / 出图记录 / 上下文快照 / 索引
    settings\     设置与上一版备份
    workflows\    导入的工作流与人工映射
    config.json   运行配置

出图原图在 `outputs\`，体积大且可由 ComfyUI 原目录找回，默认不打包；
备份包自身在 `backups\`，日志在 `logs\`，都不进备份。

删除备份不直接抹掉，移到 `backups\\_trash`，与“不自动删用户数据”一致。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import threading
import zipfile
from datetime import datetime

NAME_RE = re.compile(r"^backup-\d{8}-\d{6}(-\d+)?\.zip$")
INCLUDE_DIRS = ("history", "settings", "workflows")
INCLUDE_FILES = ("config.json",)
EXCLUDE_DIR_NAMES = {"__pycache__", ".git", "chrome_headless", "_trash",
                     "dist", "outputs", "logs", "backups"}


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(1024 * 256)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


class BackupManager:
    def __init__(self, base_dir):
        self.base_dir = os.path.abspath(base_dir)
        self.dir = os.path.join(self.base_dir, "backups")
        self.trash_dir = os.path.join(self.dir, "_trash")
        os.makedirs(self.dir, exist_ok=True)
        self._lock = threading.RLock()

    # ------------------------------------------------------------ 路径
    def path_for(self, name):
        name = str(name or "")
        if not NAME_RE.match(name):
            return None
        path = os.path.abspath(os.path.join(self.dir, name))
        if os.path.dirname(path) != os.path.abspath(self.dir):
            return None
        return path

    def _candidates(self):
        for dirname in INCLUDE_DIRS:
            root = os.path.join(self.base_dir, dirname)
            if not os.path.isdir(root):
                continue
            for current, dirs, files in os.walk(root):
                dirs[:] = [d for d in dirs if d not in EXCLUDE_DIR_NAMES]
                for fn in files:
                    if fn.endswith(".tmp"):
                        continue
                    full = os.path.join(current, fn)
                    rel = os.path.relpath(full, self.base_dir)
                    yield full, rel.replace("\\", "/")
        for fn in INCLUDE_FILES:
            full = os.path.join(self.base_dir, fn)
            if os.path.isfile(full):
                yield full, fn

    # ------------------------------------------------------------ 创建
    def create(self, note=""):
        with self._lock:
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            name = "backup-%s.zip" % stamp
            target = self.path_for(name)
            if target is None:
                raise ValueError("备份名不合法")
            if os.path.exists(target):
                index = 2
                while os.path.exists(os.path.join(self.dir, "backup-%s-%d.zip" % (stamp, index))):
                    index += 1
                name = "backup-%s-%d.zip" % (stamp, index)
                target = self.path_for(name)
            tmp = target + ".tmp"

            files = []
            counts = {key: 0 for key in INCLUDE_DIRS}
            for full, rel in self._candidates():
                item = {"path": rel, "bytes": os.path.getsize(full),
                        "sha256": _sha256(full)}
                files.append(item)
                top = rel.split("/", 1)[0]
                if top in counts:
                    counts[top] += 1
            manifest = {
                "app": "ComfyUI Prompt Workbench",
                "version": self._version(),
                "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "note": str(note or "")[:200],
                "counts": counts,
                "files": files,
                "file_count": len(files),
                "total_bytes": sum(item["bytes"] for item in files),
            }
            try:
                with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
                    for full, rel in self._candidates():
                        zf.write(full, rel)
                    zf.writestr("manifest.json",
                                json.dumps(manifest, ensure_ascii=False, indent=2))
                os.replace(tmp, target)
            finally:
                if os.path.exists(tmp):
                    try:
                        os.remove(tmp)
                    except OSError:
                        pass
            info = {
                "ok": True,
                "name": name,
                "path": target,
                "bytes": os.path.getsize(target),
                "created_at": manifest["created_at"],
                "note": manifest["note"],
                "counts": counts,
                "file_count": len(files),
            }
            return info

    def _version(self):
        try:
            from app import __version__
            return __version__
        except Exception:
            return ""

    # ------------------------------------------------------------ 列表
    def list(self):
        with self._lock:
            items = []
            if not os.path.isdir(self.dir):
                return items
            for fn in sorted(os.listdir(self.dir)):
                if not NAME_RE.match(fn):
                    continue
                path = os.path.join(self.dir, fn)
                if not os.path.isfile(path):
                    continue
                entry = {"name": fn, "bytes": os.path.getsize(path), "ok": True,
                         "created_at": datetime.fromtimestamp(
                             os.path.getmtime(path)).astimezone().isoformat(
                                 timespec="seconds"),
                         "note": "", "counts": {}, "file_count": None}
                try:
                    with zipfile.ZipFile(path) as zf:
                        bad = zf.testzip()
                        if bad is not None:
                            entry["ok"] = False
                            entry["error"] = "CRC 损坏：%s" % bad
                        else:
                            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
                            entry.update({
                                "created_at": manifest.get("created_at", entry["created_at"]),
                                "note": manifest.get("note", ""),
                                "counts": manifest.get("counts", {}),
                                "file_count": manifest.get("file_count"),
                                "version": manifest.get("version", ""),
                                "total_bytes": manifest.get("total_bytes"),
                            })
                except Exception as exc:
                    entry["ok"] = False
                    entry["error"] = "%s: %s" % (type(exc).__name__, exc)
                items.append(entry)
            items.sort(key=lambda x: x["created_at"], reverse=True)
            return items

    def info(self):
        items = self.list()
        return {"dir": self.dir, "count": len(items),
                "bytes": sum(item["bytes"] for item in items)}

    # ------------------------------------------------------------ 删除 / 读取
    def delete(self, name):
        with self._lock:
            path = self.path_for(name)
            if path is None or not os.path.isfile(path):
                return {"ok": False, "message": "备份不存在或名称不合法"}
            os.makedirs(self.trash_dir, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            target = os.path.join(self.trash_dir, "%s-%s" % (stamp, name))
            shutil.move(path, target)
            return {"ok": True, "message": "已移到 backups\\_trash，可手动找回",
                    "trashed": os.path.basename(target)}
