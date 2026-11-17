# PROJECT_CHANGELOG — 版本变更记录

本文件记录项目每次交付的变更。每次后续交付都应按下方格式追加一条记录；不得把未完成事项写成已完成。

## 记录格式

每条记录包含以下字段：

- **版本号**：语义化版本（如 `0.1.0`）；基线/准备阶段可用 `0.0.x`。
- **日期**：YYYY-MM-DD。
- **任务编号**：对应的任务书编号（如 TASK-001）。
- **分支**：提交所在分支（如 `dev`）。
- **新增功能**：本次新增的能力或文件。
- **修改文件**：本次改动的文件路径清单。
- **修复问题**：本次修复的问题；无则写“无”。
- **测试情况**：已执行的检查/测试及其结果；未测试如实写“未测试”。
- **未完成事项**：遗留项与下一阶段待办。

## 变更记录

### 0.0.1 — 2026-11-17（TASK-001，分支 dev）

- **新增功能**：
  - 建立项目控制文件：总计划、项目状态、架构与模块边界、变更记录、注入系统规范。
  - 从最新 main 创建并推送 `dev` 开发分支。
  - 归档旧项目素材保留在 `legacy-materials/`（前序提交完成，本次未改动）。
- **修改文件**：
  - `PROJECT_MASTER_PLAN.md`（新建）
  - `PROJECT_STATE.md`（新建）
  - `PROJECT_ARCHITECTURE.md`（新建）
  - `PROJECT_CHANGELOG.md`（新建，本文件）
  - `docs/PROJECT_CONTROL/INJECTION_SYSTEM_SPEC.md`（新建）
- **修复问题**：无。
- **测试情况**：
  - 远程仓库状态核对：main 最新提交 `3084866aa85595133c7a1179b15ddd71e659d8f3`；8 份基线文档与 `legacy-materials/` 在位。
  - dev 分支与 origin/dev 同步；本地工作区干净。
  - 未执行业务功能测试（尚无业务代码）。
- **未完成事项**：
  - M0 工程骨架（Tauri + React + TS + Vite + Python sidecar）尚未搭建。
  - 旧素材逐文件审查尚未完成。
  - 真机端到端验收尚未进行。

### 0.1.0-dev.1 — 2026-11-17（TASK-002，分支 dev）

- **新增功能**：
  - Python FastAPI 本地服务：会话令牌校验、设置读取/保存、存储路径校验、Ollama / ComfyUI 连接检测、管理目录初始化。
  - React + TypeScript + Vite 前端：服务健康、Ollama / ComfyUI 状态、存储位置与服务连接设置界面。
  - Tauri 2 桌面宿主骨架：`get_backend_config` 命令、随机本地端口、UUID v4 令牌、拉起自己的 Python 子进程、退出时结束该子进程（Rust 代码已落地，未在本机编译运行）。
  - 根 `.gitignore`：忽略 `.venv/`、`node_modules/`、`dist/`、Rust `target/`、`gen/`、本地日志与用户数据。
- **修改文件**：
  - 新增 `backend/requirements.txt`、`backend/main.py`、`backend/test_main.py`。
  - 新增 `frontend/package.json`、`frontend/tsconfig.json`、`frontend/tsconfig.app.json`、`frontend/tsconfig.node.json`、`frontend/vite.config.ts`、`frontend/index.html`、`frontend/src/main.tsx`、`frontend/src/App.tsx`、`frontend/src/styles.css`。
  - 新增 `frontend/src-tauri/Cargo.toml`、`frontend/src-tauri/build.rs`、`frontend/src-tauri/tauri.conf.json`、`frontend/src-tauri/capabilities/default.json`、`frontend/src-tauri/src/main.rs`、`frontend/src-tauri/src/lib.rs`。
  - 更新 `PROJECT_STATE.md`、`PROJECT_CHANGELOG.md`（本文件）。
  - 未改动 `legacy-materials/` 与既有基线文档。
- **修复问题**：无（本次未自行改写业务逻辑；后端在本机环境一次跑通，未做依赖或架构调整）。
- **测试情况**：
  - Python 语法检查：通过（`py_compile` 退出码 0）。
  - Python pytest：通过，5 passed（Python 3.13.18 / pytest 8.4.2）。
  - 后端真实 HTTP 冒烟：无/错令牌 401；正确令牌健康检查 200；设置与离线检测 200；管理目录自动创建。
  - 前端 TypeScript 检查：通过（`tsc -b` 退出码 0）。
  - 前端 Vite 构建：通过（`vite build`，33 模块）。
  - Vite dev 独立启动：127.0.0.1:1420 返回 200。
  - Rust `cargo check`：**未执行成功**，本机未安装 Rust 工具链与 MSVC C++ Build Tools。
  - 桌面窗口、sidecar 自动拉起、端口/令牌握手、退出清理：**未验证**（依赖 Rust 编译与 Tauri 运行时）。
- **未完成事项**：
  - 安装 Rust 工具链 + MSVC C++ Build Tools 后完成 Tauri 桌面闭环真机验收。
  - 固定 Python 3.12 环境并复核兼容性（本机当前为 3.13.18，无 3.12）。
  - WebView2 运行时在 Tauri 壳内的可用性待实测。
  - 业务功能（编辑器、知识库、角色管理、工作流解析、显存调度、ComfyUI 启停、安装包等）按任务书边界本次未实现。

### 0.1.0-dev.2 — 2026-11-17（TASK-002.1，分支 dev）

- **新增功能**：
  - SQLite 基础数据层：`storage.database/workbench.sqlite3`，含 `schema_version`、`app_metadata` 两表；重复初始化保留版本号。
  - 设置存储加固：10 个管理目录与外部模型路径白名单；root 由宿主固定、客户端修改返回 400；未知存储/连接键返回 400；外部模型路径留空允许、填写时必须存在且为目录。
  - 损坏配置恢复：`settings.json` 解析失败时备份为 `settings.corrupt-<时间戳>-<hex>.json` 后重建默认配置。
  - CORS 白名单：仅放行 `tauri://localhost`、`https://tauri.localhost`、`http://tauri.localhost`、`http://localhost:1420`、`http://127.0.0.1:1420`；未授权 Origin 不带 allow-origin。
  - 前端：root 输入框只读、保存前剔除只读 root；新增 `/api/storage/validate` 路径存在/目录/可写检查；合并路径行、连接列表、操作区与响应式样式。
  - Rust 宿主局部加固：数据根统一为 `%LOCALAPPDATA%\ComfyUI-Prompt-Workbench`（与后端默认根一致）；子进程 stdout/stderr 分流到 `logs/sidecar-stdout.log`、`logs/sidecar-stderr.log`；健康检查在 TCP 连通后再校验带令牌的 `/api/health`；启动失败/超时错误附带 stderr 日志路径；令牌仅经环境变量传递、不写入日志。
- **修改文件**：
  - 完整替换 `backend/main.py`、`backend/test_main.py`、`frontend/src/App.tsx`。
  - 局部修改 `frontend/src-tauri/src/lib.rs`；合并 `frontend/src/styles.css` 新样式。
  - 更新 `PROJECT_STATE.md`、`PROJECT_CHANGELOG.md`（本文件）、`PROJECT_ARCHITECTURE.md`。
  - 未改动 `legacy-materials/`、既有 8 份基线文档与 `docs/ROADMAP.md` / `PROJECT_MASTER_PLAN.md`（阶段编号 M0–M10 已核对一致，无冲突）。
- **修复问题**：
  - 修复旧版 Rust 用 `app_local_data_dir()/data`、Python 用另一目录的数据根不一致问题。
  - 修复旧版就绪判定只靠 TCP 端口打开、未校验带令牌健康端点的问题。
  - 修复损坏 `settings.json` 直接失败、无备份的问题。
- **测试情况**：
  - Python 语法检查：通过（`py_compile` 退出码 0）。
  - Python pytest：通过，13 passed，6.19s（Python 3.13.18 / pytest 8.4.2，1 条 StarletteDeprecationWarning）。
  - 后端真实 HTTP 冒烟：无/错令牌 401；正确令牌 200；CORS 白名单预检 200 带 allow-origin、未授权 Origin 400 无 allow-origin；SQLite 真实创建、两表、schema_version=1、重复初始化版本保留；root 修改 400；未知键 400；外部路径可留空；损坏配置备份并恢复；离线服务不崩溃。
  - 前端 TypeScript 检查：通过（`tsc -b` 退出码 0）。
  - 前端 Vite 构建：通过（`vite build`，33 模块，659ms）。
  - Rust `cargo check`：**未执行成功**，本机未安装 Rust 工具链与 MSVC C++ Build Tools。
  - 桌面窗口、sidecar 自动拉起、端口/令牌握手、退出清理：**未验证**（依赖 Rust 编译与 Tauri 运行时）。
- **未完成事项**：
  - 安装 Rust 工具链 + MSVC C++ Build Tools 后完成 Tauri 桌面闭环真机验收。
  - 固定 Python 3.12 环境并复核兼容性（本机当前为 3.13.18，无 3.12）。
  - WebView2 在 Tauri 壳内的可用性待实测。
  - 业务功能（编辑器、知识库、角色管理、工作流解析、显存调度、ComfyUI 启停、安装包等）按任务书边界本次未实现。

### 0.1.0-dev.3 — 2026-11-17（TASK-002.2，分支 dev）

- **新增功能**：无业务代码；完成只读 Windows 运行环境盘点、运行依赖与安装包方案整理、现状代码审查与证据归档。
- **修改文件**：
  - 新增 `docs/TASK_EVIDENCE/TASK-002.2/`（README、environment-report、runtime-dependency-report、installer-design-report、current-code-review、disk-space-report、known-issues、raw-outputs/）。
  - 更新 `PROJECT_STATE.md`（追加 TASK-002.2 盘点记录）、`PROJECT_CHANGELOG.md`（本文件）。
- **修复问题**：无（本任务不修改业务代码，不做重构）。
- **测试情况**：
  - 只读采集 OS/架构/管理员权限/磁盘/WebView2/Edge/VC++/Python/.venv/依赖清单/产物存在性；原始输出归档 `raw-outputs/`。
  - 未安装 Rust、MSVC、Node.js、Python 3.12；未修改系统 PATH/注册表/环境变量/防火墙/杀毒设置；未启停 ComfyUI/Ollama。
  - 未执行 `cargo check`、`tauri build`、PyInstaller 打包或桌面端到端运行。
- **未完成事项**：
  - 打包方案（PyInstaller sidecar、Tauri externalBin、NSIS、版本对齐、CSP、依赖拆分）由 ChatGPT 后续设计。
  - 打包环境（Rust/MSVC）与干净 Win11 x64 安装验收待后续任务。
  - 本任务不宣布 M0 桌面闭环通过，也不宣布正式 EXE 已完成。
