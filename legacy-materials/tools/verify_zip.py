# -*- coding: utf-8 -*-
"""校验阶段包：文件数、关键文件、CRC 完整性、中文名。"""

import os
import sys
import zipfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(BASE, "dist")

KEY = [
    "app/server.py", "app/prompt_context.py", "app/ollama_client.py",
    "app/lora_meta.py", "app/comfy_workflow.py", "app/output_guard.py",
    "app/history_store.py", "app/settings_store.py", "app/prompt_extract.py",
    "app/workflow_lib.py", "app/comfy_api.py", "app/vram_manager.py",
    "app/workbench_log.py", "app/runtime_state.py", "app/backup.py",
    "web/index.html", "web/style.css", "web/app.js",
    "config.json", "README_使用说明.md", "阶段2_实施记录.md", "阶段3_实施记录.md",
    "阶段4_实施记录.md", "阶段5_实施记录.md", "阶段6_实施记录.md",
    "阶段7_实施记录.md", "部署步骤_Windows.md", "更新说明.md",
    "tests/test_stage2.py", "tests/test_stage3.py", "tests/test_stage4.py",
    "tests/test_stage5.py", "tests/test_stage6.py", "tests/test_stage7.py",
    "tests/smoke_server.py", "tools/ui_probe.py",
    "AGENTS.md", "交接说明.md", "PROJECT_MANIFEST.json", "tools/check_handover.py",
    "profiles/IntoRealism_Ultra_V8.txt", "rules/模型数据库.txt",
    "rules_source/模型说明.xlsx",
]


def main():
    stage = sys.argv[1] if len(sys.argv) > 1 else "V2.0_Stage2"
    path = os.path.join(DIST, "ComfyUI_Prompt_Workbench_%s.zip" % stage)
    if not os.path.isfile(path):
        print("找不到：%s" % path)
        return 1

    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        bad = zf.testzip()
        prefix = "ComfyUI_Prompt_Workbench/"
        missing = [k for k in KEY if prefix + k not in names]
        nested = [n for n in names if n.endswith(".zip") or "/dist/" in n]
        pycache = [n for n in names if "__pycache__" in n]
        userdata = [n for n in names if any(
            n.startswith(prefix + d + "/") for d in ("history", "settings", "outputs", "backups"))]

        print("文件：%s" % path)
        print("条目数：%d" % len(names))
        print("大小：%.2f MB" % (os.path.getsize(path) / 1024 / 1024))
        print("CRC 校验：%s" % ("通过" if bad is None else "损坏 -> %s" % bad))
        print("关键文件：%s" % ("齐全" if not missing else "缺 " + "、".join(missing)))
        print("嵌套 zip / dist：%s" % ("无" if not nested else len(nested)))
        print("__pycache__：%s" % ("无" if not pycache else len(pycache)))
        print("用户数据/备份/出图：%s" % ("未打包" if not userdata else "混入 %d 个" % len(userdata)))
        print("中文文件名示例：" + "、".join(n.split("/")[-1] for n in names
                                          if any("\u4e00" <= c <= "\u9fff" for c in n))[:160])

        return 0 if (bad is None and not missing and not nested and not pycache
                     and not userdata) else 2


if __name__ == "__main__":
    sys.exit(main())
