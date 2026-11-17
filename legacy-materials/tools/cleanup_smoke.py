# -*- coding: utf-8 -*-
"""清理冒烟留下的测试会话与设置改动。

冒烟会话归档到 _archive（不删除文件），设置恢复成 20 条上下文。
"""

import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from app.history_store import HistoryStore      # noqa: E402
from app.settings_store import SettingsStore    # noqa: E402
from app.workflow_lib import WorkflowLibrary, _atomic_write  # noqa: E402
import json  # noqa: E402


def main():
    store = HistoryStore(BASE)
    archived = []
    for conv in store.list_conversations(1000):
        title = conv.get("title", "")
        if title.startswith("冒烟") or title.startswith("待删除"):
            if store.archive(conv["conversation_id"]):
                archived.append("%s %s" % (conv["conversation_id"], title))

    # 冒烟导入的工作流：删掉归档文件与残留映射
    wf_dir = os.path.join(BASE, "workflows")
    removed_wf = []
    for sub in ("_archive", "mappings", ""):
        folder = os.path.join(wf_dir, sub) if sub else wf_dir
        if not os.path.isdir(folder):
            continue
        for fn in os.listdir(folder):
            if "冒烟" in fn and fn.endswith(".json"):
                os.remove(os.path.join(folder, fn))
                removed_wf.append(os.path.join(sub or "workflows", fn))

    # 索引里只保留真实存在的工作台文件
    lib = WorkflowLibrary(BASE)
    index = lib._read_index()
    kept = {name: entry for name, entry in index.get("workflows", {}).items()
            if os.path.isfile(os.path.join(lib.lib_dir, name))}
    stale = sorted(set(index.get("workflows", {})) - set(kept))
    if stale:
        index["workflows"] = kept
        _atomic_write(lib.index_path, json.dumps(index, ensure_ascii=False, indent=2))
    print("清理索引残留：%s" % ("、".join(stale) or "无"))

    settings = SettingsStore(BASE)
    settings.save({"chat": {"history_max_messages": 20}})
    print("归档测试会话：%s" % ("；".join(archived) or "无"))
    print("清理测试工作流：%s" % ("；".join(removed_wf) or "无"))
    print("当前会话数：%d" % len(store.list_conversations(1000)))
    print("history_max_messages = %s" % settings.load()["chat"]["history_max_messages"])


if __name__ == "__main__":
    main()
