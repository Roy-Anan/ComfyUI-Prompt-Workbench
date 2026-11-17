# -*- coding: utf-8 -*-
"""
一键：从 系统提示词_Ollama精简版.txt 重新生成 Modelfile，并重建 Ollama 条目 comfyui-prompt:v1。

用法：
  python register_assistant.py              生成 Modelfile 并 ollama create 重建条目
  python register_assistant.py --build-only 只生成 Modelfile，不注册条目
"""
import io
import os
import shutil
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "系统提示词_Ollama精简版.txt")
MODELFILE = os.path.join(BASE, "Modelfile.qwen3-comfyui")
ENTRY = "comfyui-prompt:v1"


def generate_modelfile():
    system = io.open(SRC, encoding="utf-8").read().strip("\n")

    # 安全检查：源文本不能出现三引号，否则会破坏 Modelfile 的 SYSTEM 边界
    if '"""' in system:
        sys.exit("源提示词包含三引号 \"\"\"，会破坏 Modelfile 的 SYSTEM 边界，请先移除。")

    header = "\n".join([
        "# Modelfile — comfyui-prompt:v1（本地 Ollama 提示词助手，通用流程）",
        "# 用法：在本目录执行  ollama create comfyui-prompt:v1 -f Modelfile.qwen3-comfyui",
        "# 说明：规则与 13 模型索引已内置进模型；对话中只需再提供当前模型的单个 profile。",
        "# 维护：改 system 后先改 系统提示词_Ollama精简版.txt，再运行 register_assistant.py 重新生成并重建条目。",
        "# 基础模型：本机已注册 qwen3:latest（8B 量化 VL），纯本地离线。",
    ])

    params = "\n".join([
        "PARAMETER num_ctx 8192",
        "PARAMETER temperature 0.7",
        "PARAMETER top_p 0.8",
        "PARAMETER top_k 20",
    ])

    content = header + "\nFROM qwen3:latest\n\nSYSTEM \"\"\"\n" + system + "\n\"\"\"\n\n" + params + "\n"
    io.open(MODELFILE, "w", encoding="utf-8", newline="\n").write(content)
    print("[1/2] 已生成 Modelfile：%s（system %d 行）" % (os.path.basename(MODELFILE), system.count("\n") + 1))


def register():
    ollama = shutil.which("ollama") or r"C:\Users\<你的用户名>\AppData\Local\Programs\Ollama\ollama.exe"
    if not os.path.exists(ollama):
        sys.exit("未找到 ollama 可执行文件，请确认 Ollama 已安装并在 PATH 中。")

    print("[2/2] 重建条目 %s ..." % ENTRY)
    r = subprocess.run([ollama, "create", ENTRY, "-f", MODELFILE], cwd=BASE)
    if r.returncode != 0:
        sys.exit("ollama create 失败，退出码 %d" % r.returncode)
    print("完成：条目 %s 已按当前 Modelfile 重建，新开对话生效。" % ENTRY)


build_only = "--build-only" in sys.argv
generate_modelfile()
if build_only:
    print("已跳过注册（--build-only）。")
else:
    register()
