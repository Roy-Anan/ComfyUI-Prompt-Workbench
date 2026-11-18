# R17 环境报告

## 运行环境

- 操作系统：Windows（本地 PC，PowerShell 7.6.4）
- 仓库：`D:\AI\ComfyUI-Prompt-Workbench-Git`，分支 `dev`
- 后端 Python：项目 `.venv`，Python 3.13.18；pytest 8.4.2；FastAPI 0.163.1、uvicorn 0.54.0、httpx 0.28.1、pydantic 2.14.3
- 前端：Node v22.23.2 / npm 10.9.8；Vite 5.4.21；TypeScript 构建通过
- 工作台端口：17890；Ollama `127.0.0.1:11434`；ComfyUI `127.0.0.1:8188`

## 真机服务核对

- ComfyUI 0.30.2，13 个 checkpoint、3 个 LoRA（既有清单，本轮未改动模型目录）。
- 真机规则库：`userdata/database/workbench.sqlite3`；冒烟后规则表清 0，未残留测试数据。
- 临时导入的 ghost 工作流仅用于验证未登记分支，不入库为交付物。

## 未做 / 边界

- 本轮未改动 main 分支、未推送构建产物与 userdata。
- 未启用 LoRA 规则组合；未实现 LLM 提示装配、前端规则界面、冲突裁决。
