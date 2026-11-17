# 环境报告 — TASK-003.1-R2

## 执行环境

| 项 | 值 |
| --- | --- |
| 操作系统 | Windows 11 (10.0.26200) |
| 仓库本地路径 | `D:\AI\ComfyUI-Prompt-Workbench-Git` |
| 分支 | `dev` |
| Python（项目 `.venv`） | 3.13.18 |
| Node.js | v22.23.2 |
| npm | 10.9.8 |
| pytest | 8.4.2（项目 `.venv`） |
| 前端构建工具 | Vite 5.4.21，TypeScript 编译器 `tsc -b` |
| 应用版本号 | `0.1.0-dev.5`（本轮 ChatGPT 未要求改动版本号） |

## 依赖（项目既有，本轮未安装/未升级）

- `requirements.txt`：fastapi>=0.115,<1；uvicorn[standard]>=0.34,<1；httpx>=0.28,<1；pydantic>=2.10,<3
- `requirements-dev.txt`：`-r requirements.txt`；pytest>=8.3,<9

## 运行方式

- 后端：项目 `.venv` 的 `python -m uvicorn main:app --host 127.0.0.1 --port 8000`（仅回环地址）。
- 前端：由 FastAPI 同源托管 `frontend/dist`；`npm run build` 产物为 `dist/index.html`、`index-*.css`、`index-*.js`。
- 未使用 ComfyUI 自带 Python；未安装或升级 Python、Node、Rust、MSVC。

## 进程与服务边界

- 验收期间仅启动本工作台 uvicorn 实例（PID 15668，子进程记录于日志中）。
- 验收结束后通过 `scripts/workbench_stopper.py` 按身份校验停止该实例；停止后端口 8000 释放。
- ComfyUI 本身未被工作台启动、关闭或重启；验收后系统内无残留 `uvicorn main:app` / ComfyUI 命令行进程。
