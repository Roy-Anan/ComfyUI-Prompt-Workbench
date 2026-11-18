# R28 环境报告

- OS：Windows（本地 PC，PowerShell 7.6.4）
- 仓库：`D:\AI\ComfyUI-Prompt-Workbench-Git`，分支 `dev`
- 后端：项目 `.venv`，Python 3.13.18；pytest 8.4.2；FastAPI 0.163.1、uvicorn 0.54.0、httpx 0.28.1、pydantic 2.14.3
- 前端：Node v22.23.2 / npm 10.9.8；Vite 5.4.21；React 18.3.1；TypeScript 5.6.2
- 端口：工作台 17890；Ollama 127.0.0.1:11434；ComfyUI 127.0.0.1:8188
- 浏览器：内置 Aha Browser Use（bu 平面），同源访问 127.0.0.1:17890

## 真机数据

- 规则库：`userdata/database/workbench.sqlite3`，验收后清 0。
- 档案：`legacy-materials/profiles/PonyDiffusion_V6_XL.txt`。
- 本轮未调用 Ollama、未回写 Prompt、未改动模型目录。

## 边界

- main 分支未改动；未推送 userdata / dist / 模型文件。
