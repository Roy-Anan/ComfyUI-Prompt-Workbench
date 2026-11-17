# LEGACY_MATERIALS_README — 旧版工作台复用素材说明

## 1. 素材来源

- **来源项目**：早期开发后放弃的 ComfyUI Prompt Workbench（旧版 V2.0，单机 localhost 方案）。
- **原始路径**：`D:\AI\ComfyUI_Prompt_Workbench`（原文件保持不动，本次仅复制筛选副本）。
- **整理目的**：为新项目 `ComfyUI-Prompt-Workbench` 开发提供可参考的实现、规则与样例。**本目录不是新项目代码，不与新项目合并；其中任何实现都需要按新项目基线文档重新评估后再采用。**
- **整理时间**：2026-11-17。

## 2. 旧项目技术栈（按旧项目文档记录）

| 类别 | 旧版实现 |
| --- | --- |
| 后端 | Python 3.13，Python 标准库为主，HTTP 服务入口 `app/server.py` |
| 前端 | 原生 HTML / CSS / JavaScript（`web/`），无前端框架、无构建工具 |
| 数据持久化 | 本地 JSON 文件（history / settings / workflows），无数据库 |
| 本地 LLM | Ollama 桌面版 `http://127.0.0.1:11434`，模型 `comfyui-prompt:v1`（基座 `qwen3:latest`） |
| 出图服务 | 本地秋叶整合包 ComfyUI `http://127.0.0.1:8188`，HTTP + WebSocket |
| 运行方式 | `启动工作台.bat` → `app/server.py`，只监听 `127.0.0.1` |
| 打包发布 | `tools/make_release.py`、`tools/verify_zip.py` |

> 新项目基线已定的方向是 Tauri 2 + React + TypeScript + Vite + Python sidecar + SQLite，与旧版技术栈不同。旧版代码仅作逻辑、规则、交互与边界处理的参考，不能直接照搬架构。

## 3. 目录用途

### 源代码 `app/`

| 文件 | 用途（供参考） |
| --- | --- |
| `server.py` | HTTP 路由、静态页面、接口编排与启动入口（旧版最大模块） |
| `comfy_workflow.py` | UI/API 工作流解析，按连线判定正负向 Prompt 节点 |
| `workflow_lib.py` | 工作流库导入、列出、人工映射与归档 |
| `comfy_api.py` | UI Workflow 转 API Prompt、提交、轮询、取图、`/free` 释放 |
| `ollama_client.py` | Ollama 对话、卸载、预加载 |
| `vram_manager.py` | 8GB 显存状态机：卸 Ollama → 出图 → 释放 ComfyUI → 恢复 Ollama |
| `profile_lookup.py` | 按完整 checkpoint 文件名精确匹配模型档案 |
| `prompt_context.py` | 系统提示词 + 模型档案 + 对话上下文注入 |
| `prompt_extract.py` | 从助手回复切出正/负提示词与参数，不改写内容 |
| `output_guard.py` | 输出跑飞检测（长度、逗号、重复短语），只判定不改写 |
| `history_store.py` | 会话、消息、提示词、出图记录的原子持久化（JSON） |
| `settings_store.py` | 设置读写、白名单/范围校验、保存前备份 |
| `backup.py` | 备份 history/settings/workflows/config，ZIP 清单带 SHA256 |
| `workbench_log.py` | JSON 行滚动日志、内存最近 600 条、启动读回 |
| `runtime_state.py` | 当前任务、计数器、last_error |
| `lora_meta.py` | 读取 safetensors 头部识别 LoRA 架构，不按文件名猜 |

### 前端 `web/`

- `index.html`：页面结构。
- `style.css`：深色主题样式。
- `app.js`：前端交互与本地后端调用。

### 工具脚本 `tools/`

- 探针/校验类：`check_ui.py`、`ui_probe.py`、`comfy_probe.py`、`ollama_probe.py`、`wf_probe.py`、`convert_probe.py`、`extract_plan.py`。
- 流程/打包类：`make_release.py`、`verify_zip.py`、`check_handover.py`、`cleanup_smoke.py`、`register_assistant.py`。
- 演示/生成类：`chat_demo.py`、`gen_once.py`。
- `启动提示词助手.bat`：旧版启动辅助脚本。

### 测试 `tests/`

- `smoke_server.py`：冒烟服务样例。
- `test_profile_lookup.py` 与 `test_stage2.py` ~ `test_stage7.py`：各阶段单元测试样例，可参考测试组织方式。

### 规则与模型档案 `rules/`、`rules_source/`、`profiles/`

- `rules/`：系统提示词（全量版 / Ollama 精简版）、输出模板、模型数据库、模型索引、Modelfile、待核实抓取清单、模型说明表。
- `rules_source/ComfyUI_Prompt_Master_V1/`：规则包原始来源，含 `MODEL_PROFILES/`（各模型档案）、`TEMPLATES/`（新模型档案模板）、`TEST_FEEDBACK/`（反馈记录模板）。
- `profiles/`：13 份模型档案文本（与 `rules_source` 内档案对应）。

### 配置与索引样例 `settings/`、`workflows/`

- `settings/app_settings.json`（及 `.bak.json`）：旧版本地设置样例，含本机地址与默认模型名，**不含密钥**。
- `workflows/workflows_index.json`：旧版工作流库索引（空库样例）。

### 文档（根目录 `.md` / `.json` / `.bat`）

- `AGENTS.md`：旧版多智能体协作入口与变更协议。
- `PROJECT_MANIFEST.json`：旧版模块地图、命令、不变量与已知边界。
- `交接说明.md`、`README_使用说明.md`、`部署步骤_Windows.md`、`更新说明.md`、`规则包整合记录.md`。
- `阶段2_实施记录.md` ~ `阶段7_实施记录.md`：各阶段实施与验收记录。
- `config.json`：旧版运行配置样例（本机路径、Ollama/ComfyUI 地址、显存参数）。
- `启动工作台.bat`：旧版启动脚本。

## 4. 已知问题与边界（来自旧版清单，供避坑参考）

- 8GB 显存下 Ollama 与 ComfyUI 不能同时驻留；旧版用状态机串行调度。
- 旧版主题只实现深色，浅色会被强制回退到 dark。
- 备份不含 outputs 原图与 logs。
- `confirm_delete` 只是页面二次确认；直接调 API 不弹确认。
- 出图 400 校验失败也计入 errors 并写 last_error。
- 同参数同种子可能命中 ComfyUI 执行缓存，1–2 秒返回同图。
- 旧版依赖秋叶整合包内的 Python 解释器，本机无系统级 Python。
- `nvidia-smi` 首次直调可能空输出，需重定向读取。
- 阶段 1 没有单独的实施记录，记录在 `规则包整合记录.md`。
- 旧版是单机 localhost 方案，不提供公网部署、账号体系或多用户隔离。
- 旧版按完整 checkpoint 文件名精确匹配，不做关键词、前缀或相似度匹配；正负节点按连线判定，不写死节点编号。

## 5. 本次未纳入素材的内容及原因

以下内容属于运行数据、产物、缓存、隐私或大文件，**未复制到本目录**：

| 排除项 | 位置（旧项目） | 排除原因 |
| --- | --- | --- |
| 对话/历史记录 | `history/` | 含会话上下文、消息与出图记录，属个人运行数据 |
| 生成原图 | `outputs/` | 大型 PNG 出图结果，体积约 22.7 MB，非代码素材 |
| 历史备份压缩包 | `backups/` | 旧版备份 ZIP，含运行数据副本 |
| 运行日志与探针快照 | `logs/` | 运行期日志、object_info 快照、UI 截图等过程产物 |
| 发布打包产物 | `dist/` | 旧版发布 ZIP（约 3.45 MB），可由源码重新生成 |
| Python 缓存 | `app/__pycache__/`、`*.pyc` | 编译缓存，可重新生成 |
| 模型权重 / LoRA / Checkpoint | 项目外模型目录 | 大型二进制权重，不在本项目目录内，未收集 |

## 6. 安全与使用提醒

- 本目录内未发现 API 密钥、Token、密码或账号凭据；`config.json`、`settings/` 仅含本机回环地址、模型名和本机路径。
- 旧脚本中 Ollama 可执行文件路径里的本机用户名已替换为占位符 `<你的用户名>`；`config.json` 等配置中的 `D:/AI/Qiuye/ComfyUI-aki-v3.2/...` 为旧版本机绝对路径，新项目需按实际环境重新配置。
- 旧版规则文本、模型档案和提示词模板在采用前，需按新项目基线重新核对可信度与适用范围。
- 不要把旧版实现直接合并进新项目；参考时以新项目 `docs/` 基线文档为准。
