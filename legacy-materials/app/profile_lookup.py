# -*- coding: utf-8 -*-
"""ComfyUI Prompt Workbench —— Profile 精确匹配模块（阶段 1 核心交付）。

匹配规则来自项目计划书第六节：
1. 只接受「模型数据库.txt」里登记的 **完整 checkpoint 文件名**；
2. 允许去掉工作流里带的前缀目录（如 ``SDXL/xxx.safetensors``），但文件名本身必须一模一样；
3. 不做关键词、前缀、相似度或同系列版本推断（Huslyo 普通版 / DMD / V3 必须分开）；
4. 未登记 → 返回 ``unregistered``，明确提示「模型配置未登记」，绝不伪造 Profile。
"""

from __future__ import annotations

import io
import os

APP_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(APP_DIR)

DB_RELATIVE = os.path.join("rules", "模型数据库.txt")
INDEX_RELATIVE = os.path.join("rules", "模型索引_Ollama.txt")
PROFILES_RELATIVE = "profiles"


def read_text(path):
    """按 UTF-8 读取（自动吃掉 BOM）。"""
    with io.open(path, encoding="utf-8-sig") as fh:
        return fh.read()


def filename_of(path_like):
    """把 ``SDXL/xxx.safetensors`` / ``SDXL\\xxx.safetensors`` 统一成文件名。"""
    return os.path.basename(str(path_like).replace("\\", "/").strip())


class ProfileLookup:
    """checkpoint 文件名 → 单个 profile 文件。"""

    def __init__(self, base_dir=None, db_path=None, index_path=None, profiles_dir=None):
        self.base_dir = os.path.abspath(base_dir or BASE_DIR)
        self.db_path = os.path.abspath(db_path or os.path.join(self.base_dir, DB_RELATIVE))
        self.index_path = os.path.abspath(index_path or os.path.join(self.base_dir, INDEX_RELATIVE))
        self.profiles_dir = os.path.abspath(profiles_dir or os.path.join(self.base_dir, PROFILES_RELATIVE))

        self.entries = {}      # 小写文件名 -> 记录
        self.registered = []   # 按登记顺序的完整文件名
        self.index = {}        # 小写文件名 -> 索引元数据（架构/派系/画风/提示词体系/注意）
        self.problems = []     # 解析期发现的问题

        self._load_database()
        self._load_index()

    # ------------------------------------------------------------------ 载入
    def _load_database(self):
        if not os.path.isfile(self.db_path):
            raise FileNotFoundError("找不到模型数据库：%s" % self.db_path)
        category = ""
        for lineno, line in enumerate(read_text(self.db_path).splitlines(), 1):
            raw = line.strip()
            if not raw or raw.startswith("#"):
                continue
            if raw.startswith("[") and raw.endswith("]"):
                category = raw[1:-1].strip()
                continue
            if "=" not in raw:
                self.problems.append("模型数据库第 %d 行无法解析：%s" % (lineno, raw))
                continue
            name, target = raw.split("=", 1)
            checkpoint = name.strip()
            target = target.strip().replace("\\", "/")
            if not checkpoint or not target:
                self.problems.append("模型数据库第 %d 行字段为空：%s" % (lineno, raw))
                continue
            profile_file = os.path.basename(target)
            key = checkpoint.lower()
            if key in self.entries:
                self.problems.append("重复登记：%s（第 %d 行）" % (checkpoint, lineno))
                continue
            self.entries[key] = {
                "checkpoint": checkpoint,
                "profile_file": profile_file,
                "profile_path": os.path.join(self.profiles_dir, profile_file),
                "category": category,
            }
            self.registered.append(checkpoint)

    def _load_index(self):
        if not os.path.isfile(self.index_path):
            self.problems.append("找不到模型索引：%s" % self.index_path)
            return
        for line in read_text(self.index_path).splitlines():
            raw = line.strip()
            if not raw.startswith("|") or "---" in raw:
                continue
            cells = [c.strip() for c in raw.strip("|").split("|")]
            if len(cells) < 6 or cells[0] == "文件名":
                continue
            self.index[cells[0].lower()] = {
                "arch": cells[1],
                "family": cells[2],
                "style": cells[3],
                "prompt_system": cells[4],
                "notes": cells[5],
            }

    # ------------------------------------------------------------------ 查询
    def lookup(self, checkpoint_name):
        """按完整文件名精确匹配，返回 dict（ok 为 False 时带 reason/message）。"""
        raw = "" if checkpoint_name is None else str(checkpoint_name).strip()
        if not raw:
            return {"ok": False, "reason": "empty", "message": "没有提供 checkpoint 文件名"}

        name = filename_of(raw)
        record = self.entries.get(name.lower())
        if record is None:
            return {
                "ok": False,
                "input": raw,
                "checkpoint": name,
                "reason": "unregistered",
                "message": "模型配置未登记：%s 不在 模型数据库.txt 中。工作台不做模糊匹配，请先按模板建档再使用。"
                           % name,
            }

        if not os.path.isfile(record["profile_path"]):
            return {
                "ok": False,
                "input": raw,
                "checkpoint": name,
                "reason": "profile_missing",
                "registered_name": record["checkpoint"],
                "message": "已匹配到登记名 %s，但 profile 文件缺失：%s"
                           % (record["checkpoint"], record["profile_file"]),
            }

        warnings = []
        match_type = "exact"
        if name != record["checkpoint"]:
            match_type = "case-insensitive"
            warnings.append("大小写与登记名不一致（登记为 %s），按 Windows 文件名规则匹配。"
                            % record["checkpoint"])

        entry = self.index.get(record["checkpoint"].lower(), {})
        return {
            "ok": True,
            "reason": "matched",
            "match_type": match_type,
            "input": raw,
            "checkpoint": name,
            "registered_name": record["checkpoint"],
            "category": record["category"],
            "profile_file": record["profile_file"],
            "profile_path": record["profile_path"],
            "profile_relpath": os.path.relpath(record["profile_path"], self.base_dir).replace("\\", "/"),
            "arch": entry.get("arch", ""),
            "family": entry.get("family", ""),
            "style": entry.get("style", ""),
            "prompt_system": entry.get("prompt_system", ""),
            "notes": entry.get("notes", ""),
            "warnings": warnings,
        }

    def profile_text(self, checkpoint_name):
        """取匹配到的 profile 全文；未登记或文件缺失时返回 None。"""
        result = self.lookup(checkpoint_name)
        if not result.get("ok"):
            return None
        return read_text(result["profile_path"])

    def list_models(self):
        """13 个登记模型 + 索引元数据 + profile 是否存在。"""
        items = []
        for name in self.registered:
            record = self.entries[name.lower()]
            entry = self.index.get(name.lower(), {})
            items.append({
                "checkpoint": name,
                "category": record["category"],
                "profile_file": record["profile_file"],
                "profile_exists": os.path.isfile(record["profile_path"]),
                "arch": entry.get("arch", ""),
                "family": entry.get("family", ""),
                "style": entry.get("style", ""),
                "prompt_system": entry.get("prompt_system", ""),
                "notes": entry.get("notes", ""),
            })
        return items

    # ------------------------------------------------------------------ 体检
    def integrity(self, checkpoints_dir=None):
        """检查映射、profile 文件、索引三方的完整性。"""
        missing_profiles = [r["profile_file"] for r in self.entries.values()
                            if not os.path.isfile(r["profile_path"])]

        disk_profiles = []
        if os.path.isdir(self.profiles_dir):
            disk_profiles = [f for f in os.listdir(self.profiles_dir) if f.lower().endswith(".txt")]
        referenced = {r["profile_file"].lower() for r in self.entries.values()}
        orphans = sorted(f for f in disk_profiles if f.lower() not in referenced)

        index_without_db = sorted(n for n in self.index if n not in self.entries)
        db_without_index = [r["checkpoint"] for r in self.entries.values()
                            if r["checkpoint"].lower() not in self.index]

        missing_checkpoints = []
        if checkpoints_dir and os.path.isdir(checkpoints_dir):
            names = {f.lower() for f in os.listdir(checkpoints_dir)}
            missing_checkpoints = [r["checkpoint"] for r in self.entries.values()
                                   if r["checkpoint"].lower() not in names]

        return {
            "db_entries": len(self.entries),
            "profile_files": len(disk_profiles),
            "index_entries": len(self.index),
            "missing_profiles": missing_profiles,
            "orphan_profiles": orphans,
            "index_without_db": index_without_db,
            "db_without_index": db_without_index,
            "missing_checkpoints": missing_checkpoints,
            "checkpoints_dir": checkpoints_dir or "",
            "parse_problems": list(self.problems),
            "ok": not (missing_profiles or orphans or index_without_db
                       or db_without_index or missing_checkpoints or self.problems),
        }
