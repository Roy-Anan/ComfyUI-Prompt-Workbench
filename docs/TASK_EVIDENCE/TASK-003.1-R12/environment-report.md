# R12 环境报告

## 执行环境

- 操作系统：Windows（本机 ROY），PowerShell 7.6.4。
- 仓库：`D:\AI\ComfyUI-Prompt-Workbench-Git`，分支 `dev`。
- 后端：`.venv` Python 3.13.18；pytest 8.4.2；fastapi 0.163.1、pydantic 2.14.3。
- 前端：Node v22.23.2 / npm 10.9.8；Vite 5.4.21。

## 外部服务

- 本轮为纯本地解析层，未调用 ComfyUI/Ollama；未拉起工作台后端。
- ComfyUI `127.0.0.1:8188`、Ollama `127.0.0.1:11434` 保持既有在线状态。

## 基线

- 切片前 dev = origin/dev = `5e72ab8`（R11 回执回填）；main `3084866` 未改动。
