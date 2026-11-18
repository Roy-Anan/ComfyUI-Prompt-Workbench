# R18 环境报告

## 运行环境

- 操作系统：Windows（本地 PC，PowerShell 7.6.4）
- 仓库：`D:\AI\ComfyUI-Prompt-Workbench-Git`，分支 `dev`
- 后端 Python：项目 `.venv`，Python 3.13.18；pytest 8.4.2；FastAPI 0.163.1、uvicorn 0.54.0、httpx 0.28.1、pydantic 2.14.3
- 前端：Node v22.23.2 / npm 10.9.8；Vite 5.4.21；TypeScript 构建通过
- 工作台端口：17890；Ollama `127.0.0.1:11434`；ComfyUI `127.0.0.1:8188`

## 真机核对

- 真机规则库：`userdata/database/workbench.sqlite3`；冒烟后规则表清 0，未残留测试数据。
- 本轮未调用 Ollama 生成内容；未改动模型目录、未回写工作流 Prompt。

## 未做 / 边界

- 未改动 main 分支、未推送构建产物与 userdata。
- LoRA 规则组合、冲突人工裁决、载荷裁剪长度控制、动态检索、前端规则界面在后续切片。
