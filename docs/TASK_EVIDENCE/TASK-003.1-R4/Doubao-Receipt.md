# Doubao 回执 — TASK-003.1-R4（原始回执，未摘录润色）

## 一句话结论

用两份用户提供的真实 ComfyUI UI 格式样本在真机完成只读识别核对，并补齐 UI 解析中模型 / LoRA 节点的参数提取；后端 **63 passed**，前端构建 **exit 0**，Ollama 与 ComfyUI 经工作台探测均在线。API workflow 真机写入闭环仍缺一份「导出 API 格式」样本，本轮未在 UI 样本上写入。

## 执行前基线

- 仓库：`D:\AI\ComfyUI-Prompt-Workbench-Git`，远端 `https://github.com/Roy-Anan/ComfyUI-Prompt-Workbench`
- `dev = origin/dev = ea084cbd9b2dcc0b6a3df2a323878592b46cab89`
- main：`3084866aa85595133c7a1179b15ddd71e659d8f3`，未合并、未改动
- 工作区干净

## 本轮做了什么

### 1. 本机环境盘点（`D:\AI`，只读）

- ComfyUI 秋葉整合包：`D:\AI\Qiuye\ComfyUI-aki-v3.2`，入口 `ComfyUI\main.py`，内嵌 `python\python.exe`（3.13.11，PyTorch 2.13.0+cu130），模型目录 `ComfyUI\models\{checkpoints,loras}`，输出目录 `ComfyUI\output`；`extra_model_paths.yaml` 为 `{}`。
- Ollama：`C:\Users\15380\AppData\Local\Programs\Ollama`，模型 `comfyui-prompt:v1`（186e0e878f40，5.0 GB）、`qwen3:latest`（2742a351e8db，5.0 GB）。
- 其他：`D:\AI\LoRA`、`D:\AI\MODELS`、`D:\AI\SillyTavern`（酒馆）。

### 2. 真机服务拉起与探测

- Ollama 经 `ollama list` 拉起，`GET /api/tags` → 200，两个模型在册。
- ComfyUI 用内嵌 Python 后台启动 `main.py --listen 127.0.0.1 --port 8188`，约 95 秒后 `GET /system_stats` → 200，版本 0.30.2。
- 工作台 `/api/services/status`：Ollama online=200，ComfyUI online=200。

### 3. 两份真实样本识别（只读）

两份均为 UI 界面格式（根 `nodes` 数组 + `links`，无扁平 `class_type`）：

- `silver_hair_2p5d_txt2img_workflow.json`（7 节点）：CheckpointLoaderSimple 节点 1 → `RH_Illustrious_2.5D_V1.safetensors`；无 LoRA；KSampler 节点 5，positive→2、negative→3；节点 2 正向、节点 3 负向。
- `suyuexisdxl.json`（8 节点）：CheckpointLoaderSimple 节点 1 → `intorealismUltra_v80.safetensors`；LoraLoader 节点 10 → `suyuexifull_c1-st6000.safetensors`，strength_model 0.7、strength_clip 0.85；KSampler 节点 7（seed 231661496131269，steps 35，cfg 5.5，dpmpp_2m_sde，karras，denoise 1），positive→4、negative→5；SaveImage 节点 9 prefix `pony_sdxl`；节点 4 正向、节点 5 负向。
- 与 ComfyUI `/object_info` 清单核对：上述 checkpoint 与 lora 名均存在。

### 4. 后端改动（`backend/workflow_service.py`）

- 新增 `_UI_LOADER_WIDGET_ORDER`：常见加载器控件顺序兜底表。
- 新增 `_ui_widget_input_names`：跳过已被 link 绑定的占位槽，把 `widgets_values` 位置对齐到控件名；无 widget 描述时回退顺序表。
- 新增 `_ui_inputs`：仅提取 str / int / float / bool / None 标量，生成只读 `inputs`。
- `_parse_ui` 的模型 / LoRA 节点由空 `inputs` 改为调用 `_ui_inputs`；UI 工作流仍 `safe_prompt_write_supported=False`，写入边界未变。

### 5. 回归测试（`backend/test_workflow_service.py`，新增 1 例）

- `test_ui_parser_reads_loader_and_lora_widget_values`：构造 Checkpoint + LoRA UI 节点，断言 checkpoint 名、LoRA 名与双强度被正确提取，格式仍为 `ui`、不可写。

## 测试与构建结果

- 后端：`.venv\Scripts\python.exe -m pytest -q` → **63 passed, 1 warning in 2.87s**，exit 0。
  - 警告：`StarletteDeprecationWarning`（既有遗留，非本轮引入）。
- 前端：`npm run build`（`tsc -b && vite build`）→ **exit 0**，33 modules，Vite 5.4.21，✓ built in 534ms。
- 原始输出：`pytest-output.txt`、`frontend-build.txt`。

## 真机浏览器验收

- `http://127.0.0.1:17890` 打开，本地服务已连接（Python 3.13.18）。
- 截图：`screenshots/suyuexisdxl-recognized.png`（Checkpoint / LoRA / 强度）、`screenshots/suyuexisdxl-prompt-nodes.png`（节点 5 负向、节点 4 正向）、`screenshots/silver-hair-recognized.png`（Checkpoint、无 LoRA）、`screenshots/services-online.png`（Ollama / ComfyUI 在线）。

## 明确未完成 / 未验证

- API workflow 真机写入闭环（导入→确认白名单→写入→重开持久化→快照校验）仍未执行；缺一份 ComfyUI「导出 API 格式」样本，未伪造通过。
- 未实现 Ollama 对话生成 / 模型选择 / 参数配置（M4）；未实现 ComfyUI 提交 / 队列 / WebSocket 进度 / 结果拉取 / 输出目录映射（M6）。后端当前仅有 `/api/services/status` 连通性探测。
- 工作台未内置启停外部 Ollama / ComfyUI 进程的能力；本轮服务由本次验收手动拉起，遵循「工作台只连接和管理任务，不擅自控制外部进程」口径。
- `storage.checkpoint`、`storage.lora` 仍为空串；外部模型目录扫描、身份缓存与输出目录索引属 M3 / M7 / M8，本轮未做。
- 指纹规范化偏严格（数字 1/1.0、浮点精度、空值空串、链接 slot 序号）刻意未放宽，列入 backlog。
- Python 3.12 兼容性未验证（本机仅 3.13.18）；显存阈值待真机测量。

## 改动文件

- 修改：`backend/workflow_service.py`、`backend/test_workflow_service.py`
- 新增证据：`docs/TASK_EVIDENCE/TASK-003.1-R4/`（README、Doubao-Receipt、execution-report、test-results、environment-report、git-diff、git-diff-raw.txt、known-issues、pytest-output.txt、frontend-build.txt、samples/ 两份样本、screenshots/ 四张截图、logs/）

## 环境

- Windows 本机 ROY；Python 3.13.18（项目 `.venv`）；pytest 8.4.2；Node v22.23.2；npm 10.9.8；Vite 5.4.21。
- ComfyUI 0.30.2（内嵌 Python 3.13.11）；Ollama 0.40.15。
