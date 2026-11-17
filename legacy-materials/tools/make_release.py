# -*- coding: utf-8 -*-
"""打阶段包：把工作台目录压成 dist\\ComfyUI_Prompt_Workbench_<阶段>.zip。

用法：python tools\\make_release.py V2.0_Stage1
"""

import os
import sys
import zipfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(BASE, "dist")

EXCLUDE_DIRS = {"dist", "__pycache__", ".git", "history", "settings", "outputs",
               "backups", "chrome_headless"}
EXCLUDE_FILES = {"hashes_临时.txt"}
# history\ / settings\ 是用户数据，outputs\ 是出图结果，backups\ 是用户备份，
# chrome_headless\ 是无头浏览器临时目录：都不随程序包走（计划书：更新程序不覆盖用户数据）；
# logs\ 里的测试记录保留作证据。


def main():
    stage = sys.argv[1] if len(sys.argv) > 1 else "V2.0_Stage1"
    os.makedirs(DIST, exist_ok=True)
    name = "ComfyUI_Prompt_Workbench_%s.zip" % stage
    target = os.path.join(DIST, name)

    count = 0
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root, dirs, files in os.walk(BASE):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for fn in files:
                if fn in EXCLUDE_FILES:
                    continue
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, BASE)
                zf.write(full, os.path.join("ComfyUI_Prompt_Workbench", rel))
                count += 1

    size_mb = os.path.getsize(target) / (1024 * 1024)
    print("已生成：%s" % target)
    print("文件数：%d，大小：%.2f MB" % (count, size_mb))


if __name__ == "__main__":
    main()
