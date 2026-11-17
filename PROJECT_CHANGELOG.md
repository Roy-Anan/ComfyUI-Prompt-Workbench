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
