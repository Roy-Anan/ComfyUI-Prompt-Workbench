# 环境报告 — TASK-003.1-R4

## 开发机

- 操作系统：Microsoft Windows NT 10.0.26200.0（Windows 11 内核）。
- 项目虚拟环境 Python：3.13.18（`.venv`）。
- Node：v22.23.2；npm：10.9.8。
- pytest 8.4.2；FastAPI 0.163.1；uvicorn 0.54.0；httpx 0.28.1；pydantic 2.14.3；Vite 5.4.21。

## 本机外部服务（本轮真机拉起）

### Ollama

- 地址：`http://127.0.0.1:11434`
- 版本：0.40.15（`ollama` 可执行文件）。
- 模型：
  - `comfyui-prompt:v1`，ID `186e0e878f40`，5.0 GB。
  - `qwen3:latest`，ID `2742a351e8db`，5.0 GB。
- 探测：`GET /api/tags` → 200。

### ComfyUI

- 地址：`http://127.0.0.1:8188`
- 版本：0.30.2；前端包 1.47.12；模板 0.11.31。
- 内嵌 Python：3.13.11；PyTorch 2.13.0+cu130。
- 路径：`D:\AI\Qiuye\ComfyUI-aki-v3.2\ComfyUI`。
- 模型目录：`ComfyUI\models\checkpoints`、`ComfyUI\models\loras`；输出目录：`ComfyUI\output`。
- 探测：`GET /system_stats` → 200；RAM 总计 16.9 GB，空闲约 8.2 GB。

## 本机模型清单（与样本核对）

### Checkpoints（13 个，.safetensors）

anything-v5；autismmixSDXL_autismmixPony；CyberRealisticPony_V18.0_F16；GhostMix_v2.0；HuslyoRealismSDXL_v3；huslyorealismxl_v2DMD；intorealismUltra_v80；Juggernaut-XI-byRunDiffusion；juggernautXL_ragnarokBy；majicMIX realistic v7；ponyDiffusionV6XL_v6；RH_Illustrious_2.5D_V1；waiIllustriousSDXL_v170。

### LoRAs（3 个在册）

ip-adapter-faceid-plusv2_sd15_lora；suyuexi；suyuexifull_c1-st6000。

## 端口占用核对

- 工作台 17890（本项目）；Ollama 11434；ComfyUI 8188；酒馆在独立目录运行，未占用上述端口。
