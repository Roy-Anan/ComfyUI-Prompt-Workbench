# -*- coding: utf-8 -*-
"""交接结构自检：检查 AGENTS.md / PROJECT_MANIFEST.json 与真实工程是否一致。

不依赖第三方库；可选检查 dist 发布 ZIP。任何一项失败都返回退出码 1。
"""
from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
MANIFEST_PATH = BASE / "PROJECT_MANIFEST.json"
ZIP_PATH = BASE / "dist" / "ComfyUI_Prompt_Workbench_V2.0.zip"
PREFIX = "ComfyUI_Prompt_Workbench/"

errors = []
warnings = []
passes = []


def ok(msg):
    passes.append(msg)
    print("[PASS] " + msg)


def fail(msg):
    errors.append(msg)
    print("[FAIL] " + msg)


def warn(msg):
    warnings.append(msg)
    print("[WARN] " + msg)


def rel(path):
    return path.relative_to(BASE).as_posix()


def read_text(path):
    return path.read_text(encoding="utf-8")


def main():
    if not MANIFEST_PATH.is_file():
        print("[FAIL] 缺少 PROJECT_MANIFEST.json")
        return 1
    try:
        manifest = json.loads(read_text(MANIFEST_PATH))
    except json.JSONDecodeError as exc:
        print("[FAIL] PROJECT_MANIFEST.json 不是合法 JSON：%s" % exc)
        return 1
    ok("PROJECT_MANIFEST.json 是合法 JSON")

    project = manifest.get("project", {})
    version = str(project.get("version", ""))
    if not version:
        fail("manifest 缺少 project.version")
    else:
        ok("manifest 版本：%s" % version)

    # 版本必须与代码、配置一致
    init_text = read_text(BASE / "app" / "__init__.py")
    match = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", init_text)
    if not match:
        fail("app/__init__.py 找不到 __version__")
    elif match.group(1) != version:
        fail("版本不一致：app/__init__.py=%s，manifest=%s" % (match.group(1), version))
    else:
        ok("app/__init__.py 版本一致")

    config = json.loads(read_text(BASE / "config.json"))
    config_version = str(config.get("app", {}).get("version", ""))
    if config_version != version:
        fail("版本不一致：config.json=%s，manifest=%s" % (config_version, version))
    else:
        ok("config.json 版本一致")

    # 文档索引覆盖所有根目录 Markdown
    docs = set(manifest.get("docs_index", []))
    for stage in manifest.get("stages", []):
        record = stage.get("record")
        if record:
            docs.add(record)
    root_md = {rel(p) for p in BASE.glob("*.md")}
    missing_docs = sorted(docs - {d for d in docs if (BASE / d).is_file()})
    orphan_md = sorted(root_md - docs)
    if missing_docs:
        fail("文档索引指向不存在的文件：" + "、".join(missing_docs))
    else:
        ok("文档索引 %d 条均存在" % len(docs))
    if orphan_md:
        fail("根目录有未登记的 Markdown：" + "、".join(orphan_md))
    else:
        ok("根目录 Markdown 无未登记项")

    # 后端模块覆盖
    modules = set(manifest.get("app_modules", {}))
    actual_modules = {rel(p) for p in (BASE / "app").glob("*.py")}
    missing_modules = sorted(modules - actual_modules)
    orphan_modules = sorted(actual_modules - modules)
    if missing_modules:
        fail("manifest 登记的模块不存在：" + "、".join(missing_modules))
    if orphan_modules:
        fail("app/ 有未登记模块：" + "、".join(orphan_modules))
    if not missing_modules and not orphan_modules:
        ok("app/ 模块与 manifest 一致（%d 个）" % len(modules))

    # 测试文件覆盖
    tests = set(manifest.get("test_files", []))
    actual_tests = {rel(p) for p in (BASE / "tests").glob("test_*.py")}
    actual_tests.add("tests/smoke_server.py")
    missing_tests = sorted(tests - actual_tests)
    orphan_tests = sorted(actual_tests - tests)
    if missing_tests:
        fail("manifest 登记的测试不存在：" + "、".join(missing_tests))
    if orphan_tests:
        fail("tests/ 有未登记测试：" + "、".join(orphan_tests))
    if not missing_tests and not orphan_tests:
        ok("tests/ 与 manifest 一致（%d 个）" % len(tests))

    # 必带文件在源码目录存在
    required = manifest.get("package_required", [])
    missing_required = [p for p in required if not (BASE / p).is_file()]
    if missing_required:
        fail("package_required 在工程中缺失：" + "、".join(missing_required))
    else:
        ok("package_required 在工程中齐全（%d 个）" % len(required))

    # 阶段的记录与证据存在
    missing_evidence = []
    for stage in manifest.get("stages", []):
        record = stage.get("record")
        if record and not (BASE / record).is_file():
            missing_evidence.append(record)
        for item in stage.get("evidence", []):
            if not (BASE / item).is_file():
                missing_evidence.append(item)
    if missing_evidence:
        fail("阶段记录/证据缺失：" + "、".join(missing_evidence))
    else:
        ok("阶段记录与证据齐全")

    # 文档之间的关键互链
    readme = read_text(BASE / "README_使用说明.md")
    if "AGENTS.md" not in readme or "交接说明.md" not in readme:
        fail("README 缺少 AGENTS.md / 交接说明.md 的接手指针")
    else:
        ok("README 已链接交接入口")

    # 发布包检查：存在就严格校验，不存在只警告（源码目录也可独立交接）
    if not ZIP_PATH.is_file():
        warn("未找到 dist 发布包；源码结构已检查，发布包需另行生成")
    else:
        try:
            with zipfile.ZipFile(ZIP_PATH) as zf:
                names = set(zf.namelist())
                bad = zf.testzip()
                if bad is not None:
                    fail("ZIP CRC 损坏：%s" % bad)
                else:
                    ok("ZIP CRC 通过")
                missing_in_zip = [p for p in required if PREFIX + p not in names]
                if missing_in_zip:
                    fail("ZIP 缺少必带文件：" + "、".join(missing_in_zip))
                else:
                    ok("ZIP 必带文件齐全")
                excluded = manifest.get("data_policy", {}).get("package_excludes", [])
                leaked = []
                for d in excluded:
                    if d == "__pycache__":
                        leaked.extend([n for n in names if "__pycache__" in n])
                    else:
                        leaked.extend([n for n in names if n.startswith(PREFIX + d + "/")])
                if leaked:
                    fail("ZIP 混入禁止目录：%s" % len(leaked))
                else:
                    ok("ZIP 无用户数据/缓存/dist")
                nested = [n for n in names if n.endswith(".zip") or "/dist/" in n]
                if nested:
                    fail("ZIP 内含嵌套 ZIP / dist：%d 个" % len(nested))
                else:
                    ok("ZIP 无嵌套 ZIP")
                ok("ZIP 条目数：%d；大小：%.2f MB" % (len(names),
                                                    ZIP_PATH.stat().st_size / 1024 / 1024))
        except zipfile.BadZipFile as exc:
            fail("ZIP 无法读取：%s" % exc)

    print("")
    print("=" * 56)
    if errors:
        print("结果：FAIL（%d 项错误，%d 项警告）" % (len(errors), len(warnings)))
        for item in errors:
            print(" - " + item)
        return 1
    print("结果：PASS（%d 项通过，%d 项警告）" % (len(passes), len(warnings)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
