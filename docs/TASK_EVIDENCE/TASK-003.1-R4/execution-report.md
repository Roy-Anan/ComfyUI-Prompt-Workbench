# 执行报告 — TASK-003.1-R4

## 基线

- 仓库：`https://github.com/Roy-Anan/ComfyUI-Prompt-Workbench`，本地克隆 `D:\AI\ComfyUI-Prompt-Workbench-Git`。
- 起始基线：dev `ea084cbd9b2dcc0b6a3df2a323878592b46cab89`，工作区干净，本地 = origin/dev；main `3084866` 未改动。
- 端口：工作台 17890，Ollama 11434，ComfyUI 8188；未与酒馆端口冲突。

## 本机环境盘点（只读）

- ComfyUI 秋葉整合包：`D:\AI\Qiuye\ComfyUI-aki-v3.2`
  - 入口：`ComfyUI\main.py`；内嵌 Python：`python\python.exe`（3.13.11，PyTorch 2.13.0+cu130）。
  - 模型目录：`ComfyUI\models\checkpoints`、`ComfyUI\models\loras`；输出目录：`ComfyUI\output`。
  - `extra_model_paths.yaml` 为 `{}`，模型全部在自带 models 目录。
- Ollama：`C:\Users\15380\AppData\Local\Programs\Ollama`；模型 `comfyui-prompt:v1`（186e0e878f40，5.0 GB）、`qwen3:latest`（2742a351e8db，5.0 GB）。
- 其他：`D:\AI\LoRA`、`D:\AI\MODELS`（Ollama blobs/manifests）、`D:\AI\SillyTavern`（酒馆）。

## 真机服务启动与探测

- Ollama 经 `ollama list` 拉起；`GET http://127.0.0.1:11434/api/tags` 返回 200，两个模型在册。
- ComfyUI 用内嵌 Python 后台启动：`main.py --listen 127.0.0.1 --port 8188`；约 95 秒后 `GET /system_stats` 返回 200，版本 0.30.2。
- 工作台经 `/api/services/status` 探测：Ollama online=200，ComfyUI online=200（见 `screenshots/services-online.png`）。

## 样本识别结果（只读）

### `silver_hair_2p5d_txt2img_workflow.json`（UI，7 节点）

- CheckpointLoaderSimple 节点 1：`ckpt_name = RH_Illustrious_2.5D_V1.safetensors`。
- 无 LoRA 节点。
- KSampler 节点 5：positive→节点 2，negative→节点 3。
- 节点 2 正向 Prompt，节点 3 负向 Prompt。

### `suyuexisdxl.json`（UI，8 节点）

- CheckpointLoaderSimple 节点 1：`ckpt_name = intorealismUltra_v80.safetensors`。
- LoraLoader 节点 10：`lora_name = suyuexifull_c1-st6000.safetensors`，`strength_model = 0.7`，`strength_clip = 0.85`。
- KSampler 节点 7：seed 231661496131269，steps 35，cfg 5.5，sampler `dpmpp_2m_sde`，scheduler `karras`，denoise 1；positive→节点 4，negative→节点 5。
- SaveImage 节点 9：prefix `pony_sdxl`。
- 节点 4 正向 Prompt，节点 5 负向 Prompt。

## 真机清单核对

从 ComfyUI `/object_info` 拉取清单：

- `intorealismUltra_v80.safetensors` 在 checkpoints 列表中：存在。
- `suyuexifull_c1-st6000.safetensors` 在 loras 列表中：存在。
- `RH_Illustrious_2.5D_V1.safetensors` 在 checkpoints 列表中：存在。

## 代码改动

### `backend/workflow_service.py`

- 新增 `_UI_LOADER_WIDGET_ORDER`：常见加载器（Checkpoint / UNET / CLIP / VAE / LoRA）的控件顺序兜底映射。
- 新增 `_ui_widget_input_names`：按节点 `inputs` 中是否已有 link 绑定跳过占位槽，将 `widgets_values` 位置对齐到控件名；无 widget 描述时回退到加载器顺序表。
- 新增 `_ui_inputs`：只提取 str / int / float / bool / None 标量，映射为只读 `inputs`。
- `_parse_ui` 的模型节点与 LoRA节点不再返回空 `inputs`，改为调用 `_ui_inputs`。

### `backend/test_workflow_service.py`

- 新增 `test_ui_parser_reads_loader_and_lora_widget_values`：构造带 Checkpoint 与 LoRA 的 UI 节点，断言 checkpoint 名、LoRA 名与双强度被正确提取，且格式仍为 `ui`、不可写。

## 未做（边界）

- 未实现 Ollama 对话生成、ComfyUI 任务提交 / WebSocket 进度 / 结果拉取 / 输出目录映射（M4、M6）。
- 未在工作台内控制或关闭 Ollama / ComfyUI 进程；本轮为本次验收手动拉起，进程生命周期遵循既有安全口径。
- 未改动设置页中的外部模型目录字段；`storage.checkpoint`、`storage.lora` 仍为空串，留待设置页对接。
