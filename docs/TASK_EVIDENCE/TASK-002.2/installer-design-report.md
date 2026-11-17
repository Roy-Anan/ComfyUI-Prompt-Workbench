# 安装包设计报告 — 目标交付形态与规划

- 采集时间：2026-11-17 21:59（UTC+8）
- 性质：**计划目标与规划建议**，不代表当前已完成；当前未构建正式 EXE。

## 1. 目标交付形态（规划）

| 项 | 目标 |
| --- | --- |
| 平台 | Windows x64 桌面软件 |
| 桌面框架 | Tauri 2.x |
| 前端 | React 18 + TypeScript + Vite（静态产物嵌入 Tauri） |
| 后端 | Python FastAPI，经 **PyInstaller** 打包为独立 sidecar 进程 |
| 本地存储 | SQLite（`storage.database/workbench.sqlite3`）+ 本地目录与 JSON 配置 |
| 安装程序 | NSIS 安装包 EXE（Tauri 官方支持的 Windows 打包方式之一，最终选型由 ChatGPT 设计确认） |
| 交付边界 | 只交付工作台本体；不携带 ComfyUI、Ollama、模型权重 |

## 2. 当前代码与打包相关现状（已核对）

### 2.1 Tauri 配置（`frontend/src-tauri/tauri.conf.json`）

- `productName`：ComfyUI Prompt Workbench
- `version`：0.1.0
- `identifier`：com.royanan.comfyui-prompt-workbench
- `build.devUrl`：http://127.0.0.1:1420；`frontendDist`：`../dist`
- `bundle.active`：**false**（当前尚未配置打包产物；安装包、图标、sidecar 注册等打包配置待补）
- 窗口：1180×820，最小 760×620，可缩放；`security.csp` 当前为 null（安全基线待后续阶段收紧）

### 2.2 Rust sidecar 启动代码（`src/lib.rs`）

- 随机本地端口（TCP 绑定 `127.0.0.1:0` 取空闲端口）；UUID v4 会话令牌；后端仅绑 `127.0.0.1`。
- 后端通过环境变量 `WORKBENCH_SESSION_TOKEN`、`WORKBENCH_DATA_ROOT` 传入；令牌不写日志。
- 子进程 stdout/stderr 分流到数据根 `logs/sidecar-stdout.log`、`logs/sidecar-stderr.log`。
- 健康检查：TCP 连通后再以 Bearer 令牌请求 `/api/health`，返回 200 且体含 `ok:true` 才判定就绪。
- 退出事件只结束本应用自己创建的 child，不按进程名批量结束 Python / Ollama / ComfyUI。
- 当前 `find_python` 优先取环境变量 `WORKBENCH_PYTHON`，其次项目 `.venv\Scripts\python.exe`，否则回退系统 `python`。**这套逻辑面向开发运行；正式打包后应改为启动 PyInstaller 生成的 sidecar 可执行文件，不再依赖本机 Python。**

### 2.3 Python 后端（`backend/main.py`）

- 环境变量：`WORKBENCH_SESSION_TOKEN`、`WORKBENCH_DATA_ROOT`；默认数据根 `%LOCALAPPDATA%\ComfyUI-Prompt-Workbench`。
- 数据目录：database / knowledge / prompts / workflows / drafts / history / cache / logs / backups / exports，外加可选 checkpoint / lora 扫描目录。
- SQLite：`storage.database/workbench.sqlite3`，表 `schema_version`、`app_metadata`。
- 配置：`settings.json`；损坏时备份为 `settings.corrupt-<时间戳>-<hex>.json`。

## 3. PyInstaller sidecar 可行性评估（规划，未实测）

- **能否打包**：后端依赖 FastAPI / Uvicorn / httpx / Pydantic / Starlette，均为纯 Python 包，PyInstaller 可打包；Uvicorn 标准模式、watchfiles/httptools/websockets 等扩展模块需要在打包时核对 hidden-import 与二进制收集。
- **当前未做的事**：仓库内尚无 PyInstaller spec / 打包脚本；尚未生成单文件或目录模式的后端产物；sidecar 启动参数、工作目录、端口与令牌传递方式需要在打包实现阶段对齐。
- **Tauri 能否启动打包后的 sidecar**：架构上可行——Tauri 2 支持把外部二进制作为 sidecar / external binary 随包分发并由 Rust 侧拉起；具体目录约定、`externalBin` 配置、文件名与目标三元组（`x86_64-pc-windows-msvc`）由打包设计实现。
- **sidecar 是否需要额外 DLL**：取决于 PyInstaller 产物链接的 VC++ 运行时与扩展模块；需在干净 x64 环境实测依赖（见 `runtime-dependency-report.md` 第 8 节）。

## 4. WebView2 与 VC++ Runtime

- **WebView2**：Tauri 2 在 Windows 依赖 WebView2 Runtime。可使用 Evergreen Runtime（系统已有则复用，缺失时引导安装）或随包 Fixed Version Runtime；策略与体积在打包阶段定。本机当前已装 157.0.4341.46。
- **VC++ Runtime**：Rust 二进制与 PyInstaller 后端可能依赖 v14 可再发行包；是否捆绑以实际产物在干净系统上的 DLL 检查为准。本机已检测到 v14 x64/x86，但不能据此推断干净目标机状态。

## 5. 数据目录与卸载保护（规划规则）

### 5.1 用户数据位置原则

- 用户数据**不放在安装目录**；安装目录应视为可被升级覆盖的程序文件。
- 默认数据根使用 Windows 用户可写位置：`%LOCALAPPDATA%\ComfyUI-Prompt-Workbench`（当前代码已按此默认值）。
- 数据域：`settings.json`、SQLite 数据库、knowledge、prompts、workflows、drafts、history、cache、logs、backups、exports。

### 5.2 升级保护

- 更新 / 覆盖安装**不得**删除或覆盖用户配置、数据库、Prompt、草稿、历史记录、备份与导出。
- 配置与数据库走数据根，不进入程序安装目录；升级包只替换程序文件。

### 5.3 卸载保护

- 卸载程序**不得默认删除**用户数据；如需提供“清除用户数据”选项，应作为用户显式勾选的可选项，默认不勾选。
- 模型扫描目录（checkpoint / lora）指向用户自有的模型位置，卸载工作台不删除这些模型。

### 5.4 安装权限

- 规划优先采用每用户安装（per-user，免管理员）；若采用全机器安装才需要提权。当前进程为非管理员（见环境报告）。

## 6. 安装包体积估算（估算，非实测）

> 以下为依据当前源码与既有产物的粗估区间，**不确定性较高**；最终体积以打包后的真实产物与压缩包为准。估算不含任何模型权重。

| 组成 | 估算依据 | 粗估区间（未压缩） |
| --- | --- | --- |
| Tauri 主程序本体（Rust 原生） | Tauri 2 原生二进制通常为个位数到十几 MB 量级；本机未编译，无实测 | 5–15 MB |
| 前端静态资源 | 现有 `dist/` 实测约 0.1 MB（JS 148.6 KB + CSS 2.8 KB + HTML） | < 1 MB |
| PyInstaller Python sidecar | 当前 `.venv` 约 28.3 MB（含 pytest、开发依赖等）；正式打包应裁剪测试依赖，只保留运行时依赖；Python 运行时 + FastAPI/Uvicorn/Pydantic 等 | 15–40 MB（裁剪后） |
| SQLite 与配置 | 标准库内置；初始库与 JSON 配置很小 | < 1 MB |
| VC++ Runtime（若捆绑） | 可再发行包体积按 Microsoft 官方包计，通常数 MB；也可不捆绑而依赖系统 | 0–5 MB（可选） |
| WebView2 Fixed Version（若随包） | Fixed Version 运行时体积较大；Evergreen 方案则不随包 | 0（Evergreen）或数十 MB（Fixed Version，可选） |
| NSIS 安装包压缩 | 上述内容经压缩后通常小于未压缩合计 | 压缩后整体粗估 20–50 MB（不含 WebView2 Fixed Version） |

### 明确不打入安装包的内容

- Ollama 模型、Checkpoint、LoRA、ComfyUI 模型权重与预览图。
- 秋叶整合包文件、其他项目虚拟环境、缓存、日志、导出的用户数据。
- 开发依赖（pytest、typescript、vite、node_modules、target 构建目录）。

## 7. 待 ChatGPT 设计 / 实现的打包事项

1. PyInstaller spec：入口、hidden-import、二进制收集、单文件/目录模式、sidecar 命名与版本。
2. Tauri `externalBin` / sidecar 注册、目录与权限；生产模式后端启动路径（去掉对 `.venv` / 系统 Python 的依赖）。
3. NSIS 安装配置：产品名、标识、安装目录选择、开始菜单、卸载项、数据目录不默认删除、可选 VC++ / WebView2 处理。
4. 版本号对齐：`tauri.conf.json` 0.1.0 与后端 `APP_VERSION` 0.1.0-dev.2 的发布版本策略。
5. 干净 Windows x64 虚拟机/机器上的首启动验收清单。

## 8. 不确定性声明

- 本报告所有体积为区间估算，未在打包环境实测；Rust 主程序与 PyInstaller 产物均未在本机生成。
- 运行时依赖（VC++ / WebView2）的最终捆绑策略需以实际打包产物在干净系统的检测结果为准。
- 本报告不构成“正式 EXE 已可交付”的结论。
