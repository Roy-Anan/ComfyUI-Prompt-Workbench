# -*- coding: utf-8 -*-
r"""阶段 3 / 阶段 5：对话、提示词与出图记录的本地持久化。

落盘结构（对齐计划书「十三、历史记录与数据持久化」）：

    history\
      conversations\<conversation_id>.json      一次对话一条
      prompts\<prompt_id>.json                  一次应答里抽出的正/负提示词
      history_index.json                        列表页用的轻量索引
      conversations\_archive\                   删除时移到这里，不直接抹掉

对话字段：conversation_id / title / created_at / updated_at / messages /
checkpoint / profile_name / workflow_id
提示词字段：prompt_id / conversation_id / positive / negative / checkpoint / profile / created_at

写入一律「临时文件 + os.replace」，断电或崩溃不会留半截 JSON。
"""

from __future__ import annotations

import json
import os
import random
import re
import shutil
import threading
import time
from datetime import datetime

CONV_RE = re.compile(r"^c-\d{8}-\d{6}-[0-9a-f]{4}$")
PROMPT_RE = re.compile(r"^p-\d{8}-\d{6}-[0-9a-f]{4}$")
GEN_RE = re.compile(r"^g-\d{8}-\d{6}-[0-9a-f]{4}$")


def now_iso():
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def _atomic_write(path, payload):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


class HistoryStore:
    def __init__(self, base_dir):
        self.base_dir = os.path.abspath(base_dir)
        self.conv_dir = os.path.join(self.base_dir, "history", "conversations")
        self.prompt_dir = os.path.join(self.base_dir, "history", "prompts")
        self.archive_dir = os.path.join(self.conv_dir, "_archive")
        self.gen_dir = os.path.join(self.base_dir, "history", "generations")
        self.context_dir = os.path.join(self.base_dir, "history", "contexts")
        self.index_path = os.path.join(self.base_dir, "history", "history_index.json")
        for d in (self.conv_dir, self.prompt_dir, self.gen_dir, self.context_dir,
                  self.archive_dir):
            os.makedirs(d, exist_ok=True)
        self._lock = threading.RLock()

    # ------------------------------------------------------------ 基础
    def _new_id(self, prefix):
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        return "%s-%s-%04x" % (prefix, stamp, random.randint(0, 0xFFFF))

    def _conv_path(self, cid):
        if not isinstance(cid, str) or not CONV_RE.match(cid):
            return None
        return os.path.join(self.conv_dir, cid + ".json")

    def _prompt_path(self, pid):
        if not isinstance(pid, str) or not PROMPT_RE.match(pid):
            return None
        return os.path.join(self.prompt_dir, pid + ".json")

    # ------------------------------------------------------------ 对话
    def create(self, title="", checkpoint="", profile_name="", workflow_id=""):
        with self._lock:
            cid = self._new_id("c")
            while os.path.exists(self._conv_path(cid)):
                cid = self._new_id("c")
            conv = {
                "conversation_id": cid,
                "title": (title or "未命名对话").strip()[:80],
                "created_at": now_iso(),
                "updated_at": now_iso(),
                "checkpoint": checkpoint or "",
                "profile_name": profile_name or "",
                "workflow_id": workflow_id or "",
                "messages": [],
                "prompt_ids": [],
            }
            _atomic_write(self._conv_path(cid), conv)
            self.rebuild_index()
            return conv

    def load(self, cid):
        path = self._conv_path(cid)
        if not path or not os.path.isfile(path):
            return None
        with open(path, encoding="utf-8-sig") as fh:
            return json.load(fh)

    def save(self, conv):
        path = self._conv_path(conv.get("conversation_id"))
        if not path:
            raise ValueError("非法 conversation_id：%r" % conv.get("conversation_id"))
        conv["updated_at"] = now_iso()
        _atomic_write(path, conv)
        self.rebuild_index()
        return conv

    def append_message(self, cid, role, content, meta=None, prompt_id=None):
        with self._lock:
            conv = self.load(cid)
            if conv is None:
                return None
            seq = len(conv["messages"]) + 1
            item = {"role": role, "content": content, "at": now_iso(), "seq": seq}
            if meta:
                item["meta"] = meta
            if prompt_id:
                item["prompt_id"] = prompt_id
                conv.setdefault("prompt_ids", []).append(prompt_id)
            conv["messages"].append(item)
            # 只有用户没命名时才用第一句话当标题，别覆盖手动改的名字
            if role == "user" and len(conv["messages"]) == 1 and \
                    conv.get("title") in ("", None, "未命名对话"):
                conv["title"] = (content.strip().splitlines() or ["未命名对话"])[0][:40]
            self.save(conv)
            return conv

    def drop_last_assistant(self, cid):
        """重新生成用：去掉最后一条 assistant 回复。"""
        with self._lock:
            conv = self.load(cid)
            if not conv or not conv["messages"]:
                return None
            if conv["messages"][-1]["role"] != "assistant":
                return conv
            conv["messages"].pop()
            self.save(conv)
            return conv

    def rename(self, cid, title):
        with self._lock:
            conv = self.load(cid)
            if conv is None:
                return None
            conv["title"] = (title or "").strip()[:80] or conv["title"]
            return self.save(conv)

    def archive(self, cid):
        """删除对话：移到 _archive，不直接删文件（计划书：删除需确认、不自动删数据）。"""
        with self._lock:
            path = self._conv_path(cid)
            if not path or not os.path.isfile(path):
                return False
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            target = os.path.join(self.archive_dir, "%s.deleted-%s.json" % (cid, stamp))
            shutil.move(path, target)
            self.rebuild_index()
            return True

    # ------------------------------------------------------------ 提示词
    def save_prompt(self, conversation_id, positive, negative, settings="",
                    checkpoint="", profile="", source_message_seq=None):
        with self._lock:
            pid = self._new_id("p")
            rec = {
                "prompt_id": pid,
                "conversation_id": conversation_id,
                "positive": positive or "",
                "negative": negative or "",
                "settings": settings or "",
                "checkpoint": checkpoint or "",
                "profile": profile or "",
                "created_at": now_iso(),
                "source_message_seq": source_message_seq,
            }
            _atomic_write(self._prompt_path(pid), rec)
            conv = self.load(conversation_id)
            if conv:
                conv.setdefault("prompt_ids", []).append(pid)
                self.save(conv)
            self.rebuild_index()
            return rec

    def list_prompts(self, conversation_id=None):
        items = []
        for fn in os.listdir(self.prompt_dir):
            if not fn.endswith(".json"):
                continue
            try:
                with open(os.path.join(self.prompt_dir, fn), encoding="utf-8-sig") as fh:
                    rec = json.load(fh)
            except Exception:
                continue
            if conversation_id and rec.get("conversation_id") != conversation_id:
                continue
            items.append(rec)
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return items

    # ------------------------------------------------------------ 索引 / 列表
    def rebuild_index(self):
        convs = []
        for fn in os.listdir(self.conv_dir):
            if not fn.endswith(".json"):
                continue
            try:
                with open(os.path.join(self.conv_dir, fn), encoding="utf-8-sig") as fh:
                    conv = json.load(fh)
            except Exception:
                continue
            convs.append({
                "conversation_id": conv.get("conversation_id", fn[:-5]),
                "title": conv.get("title", ""),
                "created_at": conv.get("created_at", ""),
                "updated_at": conv.get("updated_at", ""),
                "checkpoint": conv.get("checkpoint", ""),
                "profile_name": conv.get("profile_name", ""),
                "workflow_id": conv.get("workflow_id", ""),
                "message_count": len(conv.get("messages", [])),
                "prompt_count": len(conv.get("prompt_ids", [])),
                "generation_count": len(conv.get("generation_ids", [])),
            })
        convs.sort(key=lambda x: x.get("updated_at", ""), reverse=True)

        prompts = [{"prompt_id": p["prompt_id"], "conversation_id": p["conversation_id"],
                    "created_at": p["created_at"], "checkpoint": p.get("checkpoint", "")}
                   for p in self.list_prompts()]

        index = {"updated_at": now_iso(), "conversations": convs, "prompts": prompts}
        _atomic_write(self.index_path, index)
        return index

    def list_conversations(self, limit=100):
        with self._lock:
            index = self.rebuild_index()
            return index["conversations"][:limit]

    def stats(self):
        convs = [fn for fn in os.listdir(self.conv_dir) if fn.endswith(".json")]
        archived = [fn for fn in os.listdir(self.archive_dir) if fn.endswith(".json")] \
            if os.path.isdir(self.archive_dir) else []
        prompts = [fn for fn in os.listdir(self.prompt_dir) if fn.endswith(".json")]
        gens = [fn for fn in os.listdir(self.gen_dir) if fn.endswith(".json")] \
            if os.path.isdir(self.gen_dir) else []
        return {"conversations": len(convs), "archived": len(archived),
                "prompts": len(prompts), "generations": len(gens),
                "dir": os.path.join(self.base_dir, "history")}

    # ------------------------------------------------------------ 生成记录
    def _gen_path(self, gid):
        if not isinstance(gid, str) or not GEN_RE.match(gid):
            return None
        return os.path.join(self.gen_dir, gid + ".json")

    def save_generation(self, conversation_id, data):
        """落盘一次出图：参数、prompt_id、图片路径、状态。"""
        with self._lock:
            gid = self._new_id("g")
            while os.path.exists(self._gen_path(gid)):
                gid = self._new_id("g")
            rec = {
                "generation_id": gid,
                "conversation_id": conversation_id or "",
                "created_at": now_iso(),
                "updated_at": now_iso(),
                "status": "running",
                "attempts": 1,
            }
            rec.update({k: v for k, v in (data or {}).items()
                        if k not in ("generation_id", "created_at", "updated_at")})
            _atomic_write(self._gen_path(gid), rec)
            if conversation_id:
                conv = self.load(conversation_id)
                if conv:
                    conv.setdefault("generation_ids", []).append(gid)
                    self.save(conv)
            self.rebuild_index()
            return rec

    def load_generation(self, gid):
        path = self._gen_path(gid)
        if not path or not os.path.isfile(path):
            return None
        try:
            with open(path, encoding="utf-8-sig") as fh:
                return json.load(fh)
        except Exception:
            return None

    def update_generation(self, gid, patch):
        with self._lock:
            rec = self.load_generation(gid)
            if rec is None:
                return None
            rec.update(patch or {})
            rec["updated_at"] = now_iso()
            _atomic_write(self._gen_path(gid), rec)
            return rec

    def list_generations(self, conversation_id=None, limit=100):
        items = []
        if not os.path.isdir(self.gen_dir):
            return items
        for fn in os.listdir(self.gen_dir):
            if not fn.endswith(".json"):
                continue
            try:
                with open(os.path.join(self.gen_dir, fn), encoding="utf-8-sig") as fh:
                    rec = json.load(fh)
            except Exception:
                continue
            if conversation_id and rec.get("conversation_id") != conversation_id:
                continue
            items.append(rec)
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return items[:limit]

    # ------------------------------------------------------------ 上下文快照
    def save_context_snapshot(self, cid, extra=None):
        """出图前把对话上下文落一份，证明“保存上下文 → 恢复对话”这条链路。"""
        conv = self.load(cid) if cid else None
        if cid and conv is None:
            return None
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]
        name = "%s-%s.json" % (cid or "no-conv", stamp)
        path = os.path.join(self.context_dir, name)
        payload = {
            "conversation_id": cid or "",
            "created_at": now_iso(),
            "message_count": len((conv or {}).get("messages") or []),
            "messages": (conv or {}).get("messages") or [],
            "prompt_ids": (conv or {}).get("prompt_ids") or [],
            "generation_ids": (conv or {}).get("generation_ids") or [],
            "checkpoint": (conv or {}).get("checkpoint", ""),
            "profile_name": (conv or {}).get("profile_name", ""),
            "workflow_id": (conv or {}).get("workflow_id", ""),
        }
        if extra:
            payload.update(extra)
        _atomic_write(path, payload)
        return {"path": os.path.relpath(path, self.base_dir).replace("\\", "/"),
                "name": name, "message_count": payload["message_count"]}

    # ------------------------------------------------------------ 上下文
    def history_for_ollama(self, cid, limit=20, exclude_last=False):
        """取最近 N 条消息做多轮上下文；服务端读盘，不依赖浏览器内存。"""
        conv = self.load(cid)
        if not conv:
            return []
        msgs = conv["messages"]
        if exclude_last and msgs:
            msgs = msgs[:-1]
        picked = [{"role": m["role"], "content": m["content"]}
                  for m in msgs[-limit:] if m.get("content")]
        return picked

    def export_markdown(self, cid):
        conv = self.load(cid)
        if not conv:
            return None
        lines = ["# %s" % conv.get("title", "未命名对话"), ""]
        lines.append("- 对话 ID：`%s`" % conv["conversation_id"])
        lines.append("- Checkpoint：`%s`" % conv.get("checkpoint", "—"))
        lines.append("- Profile：`%s`" % conv.get("profile_name", "—"))
        lines.append("- 工作流：`%s`" % conv.get("workflow_id", "—"))
        lines.append("- 创建 / 更新：%s / %s" % (conv.get("created_at", ""),
                                                 conv.get("updated_at", "")))
        lines += ["", "---", ""]
        for m in conv.get("messages", []):
            who = "我" if m["role"] == "user" else "提示词助手"
            lines.append("## %s · %s" % (who, m.get("at", "")))
            lines.append("")
            lines.append(m.get("content", ""))
            lines.append("")
        return "\n".join(lines)
