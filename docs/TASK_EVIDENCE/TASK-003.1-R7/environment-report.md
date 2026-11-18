# 环境报告 — TASK-003.1-R7

## 开发机

- 操作系统：Windows 11（NT 10.0.26200.0）。
- 项目虚拟环境 Python：3.13.18（`.venv`）。
- Node：v22.23.2；npm：10.9.8。
- pytest 8.4.2；FastAPI 0.163.1；uvicorn 0.54.0；httpx 0.28.1；pydantic 2.14.3；Vite 5.4.21。

## 本机外部服务

### Ollama

- 地址：`http://127.0.0.1:11434`；模型 `comfyui-prompt:v1`、`qwen3:latest`。
- 本轮仅沿用既有连通性探测，未调用对话生成。

### ComfyUI

- 地址：`http://127.0.0.1:8188`；版本 0.30.2；内嵌 Python 3.13.11。
- 路径：`D:\AI\Qiuye\ComfyUI-aki-v3.2\ComfyUI`；模型目录 `models\checkpoints`、`models\loras`；输出目录 `ComfyUI\output`。
- 本轮清单：Checkpoint 13、LoRA 3、VAE 3、CLIP 0。

### 工作台

- 地址：`http://127.0.0.1:17890`；本轮验收由启动器拉起（PID 28152），版本 `0.1.0-dev.5`。
- 数据根目录：`userdata/`（被 gitignore，不入库）。
- 身份库 SQLite：`userdata/database/workbench.sqlite3`，表 `model_identity`。
- 外部模型目录设置 `storage.checkpoint`、`storage.lora` 验收后恢复空串。

## 验收数据来源

- 身份摘要与按需哈希结果：真机会话调用 + 身份库直读，见 `samples/identity-summary.json`。
