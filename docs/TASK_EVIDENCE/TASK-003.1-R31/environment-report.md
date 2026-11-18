# R31 环境报告

## 执行环境

- 操作系统：Windows（本地 PC，ROY）
- Shell：PowerShell 7.6.4（pwsh）
- 仓库：`D:\AI\ComfyUI-Prompt-Workbench-Git`，分支 `dev`
- Git：`C:\Program Files\Git\cmd\git.exe`，身份 Roy-Anan / 1538072315@qq.com

## 运行时

- 后端 Python：3.13.18（项目 `.venv`）
- pytest：8.4.2；FastAPI 0.163.1；uvicorn 0.54.0；httpx 0.28.1；pydantic 2.14.3
- 前端：Node v22.23.2，npm 10.9.8，Vite 5.4.21
- 后端版本：`0.1.0-dev.5`
- 工作台端口：17890（127.0.0.1）

## 外部服务（仅连通探测）

- Ollama：`127.0.0.1:11434`（在线）
- ComfyUI：`127.0.0.1:8188`（在线）

## 数据与产物

- 真机规则库：`userdata/database/workbench.sqlite3`；本切片结束后 `workbench_rule` 计数 0。
- 前端构建产物位于 `frontend/dist`（gitignore，不入库）。
- 样本载荷：`samples/compare-payload.json`。
