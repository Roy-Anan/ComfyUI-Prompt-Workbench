# 执行报告 — TASK-003.1-R6

## 基线

- 仓库：`D:\AI\ComfyUI-Prompt-Workbench-Git`，远端 `https://github.com/Roy-Anan/ComfyUI-Prompt-Workbench`。
- 起始基线：本地 dev = origin/dev `28f958c`，工作区干净；main `3084866` 未改动。
- 端口：工作台 17890，Ollama 11434，ComfyUI 8188。

## 真机侦察

- `GET http://127.0.0.1:8188/object_info`：模型选项位于节点 `input.required.<widget>[0]` 列表，widget 列表形态为 `[ [options...], {widget info} ]`，取值取 `val[0]`。
- 真机在册：Checkpoint 13 个 `.safetensors`；LoRA 3 个；VAE 3 项；CLIP 节点选项为空。
- 设置中 `storage.checkpoint`、`storage.lora` 仍为空串（外部目录未配置）。

## 代码改动

### 新增 `backend/model_catalog.py`

- 定义分组 widget 映射：
  - `CHECKPOINT_WIDGETS`：CheckpointLoaderSimple / CheckpointLoader / UNETLoader；
  - `CLIP_WIDGETS`：DualCLIPLoader / CLIPLoader；
  - `VAE_WIDGETS`：VAELoader；
  - `LORA_WIDGETS`：LoraLoader / LoraLoaderModelOnly。
- `_widget_options`：从 required widget 取文件名选项列表，容错非列表形态。
- `_extract_options`：跨节点聚合某分组的去重排序文件名。
- `_index_directory`：只读列出目录直下层权重文件（`.safetensors/.ckpt/.pt/.pth/.bin/.gguf`）；目录缺失/无效返回空集，不报错。
- `_annotate`：配置了目录时标记 `on_disk: true/false`；未配置目录标记 `on_disk: null`（未知，不是 false）。
- `fetch_catalog`：拉取 `/object_info`，分组并标注；ComfyUI 不可达时返回 `online:false` + 空清单 + 错误文本，不抛 500。

### `backend/main.py`

- 引入 `model_catalog`；新增 `GET /api/models/catalog`（需本地会话），读取设置中的 ComfyUI 地址与外部 checkpoint/lora 目录后调用 `fetch_catalog`。

### `backend/test_model_catalog.py`（新增 5 例）

- `test_catalog_extracts_checkpoint_lora_and_vae_options`：分组提取正确，VAE 不混入 Checkpoint。
- `test_catalog_marks_on_disk_only_when_directory_configured`：配置目录后存在/缺失分别为 true/false；未配置为 null。
- `test_catalog_unreachable_comfyui_reports_offline`：不可达时 `online:false`、四组清单为空、带错误文本。
- `test_catalog_endpoint_requires_session`：未带会话访问接口返回 401。
- `test_catalog_endpoint_returns_injected_catalog`：接口透传注入的目录结果。

### 前端 `frontend/src/App.tsx` / `styles.css`

- 新增 `ModelCatalog` 类型（checkpoints/clips/vaes/loras）与 `diskLabel` 辅助；首载并行拉取 `/api/models/catalog`。
- 设置页新增「模型清单（只读）」面板，三列展示 Checkpoint / LoRA / VAE；每项显示文件名与存在性状态；ComfyUI 离线时显示错误；CLIP 真机为空，后端返回但前端不单独成列。
- 响应式网格：宽屏三列，中屏两列，窄屏单列。

## 真机闭环（127.0.0.1:17890）

1. 工作台重新拉起（PID 12076），加载新代码。
2. `/api/models/catalog` 返回：online=true；checkpoints 13、clips 0、vaes 3、loras 3（见 `samples/catalog-summary.json`）。
3. 存在性核对：临时把 `storage.checkpoint` / `storage.lora` 指向 ComfyUI 真实 `models\checkpoints`、`models\loras`，接口返回 13 checkpoint 与 3 LoRA 全部 `on_disk=true`；核对后恢复为空串，原设置未被改写。
4. 浏览器渲染：Checkpoint（13）、LoRA（3）、VAE（3）三组名单与「目录未配置」状态正确；截图见 `screenshots/`。

## 进程处理记录

- 上一实例（PID 13660）加载的是旧分组代码，需重启加载新逻辑。停止脚本因既有缺陷（运行记录 `creation_date=null`、CIM 身份信息读取失败）未能自动回收；手动核对命令行/可执行路径/工作目录/端口后，确认为本工作台 venv 的 uvicorn 实例，回收根进程 13660 与其工作子进程 8224，并清理 `.workbench.pid` / `.workbench-runtime.json`。ComfyUI（8188）、Ollama（11434）未触碰，核对仍为 200。

## 未做（边界）

- SHA256 身份记录、规则继承与冲突检测、动态检索、云端资料导入审核，均属后续 M3 切片。
- 未实现 Ollama 对话生成（M4）、ComfyUI 提交/队列/进度/结果/输出目录索引（M6）。
