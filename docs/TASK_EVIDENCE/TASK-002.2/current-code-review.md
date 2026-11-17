# 当前代码审查 — 现状核对与问题记录

- 审查时间：2026-11-17 21:59（UTC+8）
- 范围：当前 `dev`（基线 `5cd4441092bd4f874720b3be0e8e95dcf34ae704`）的 Tauri 配置、Rust sidecar、Python 后端、前端配置
- 原则：只记录问题、影响与复现条件；**不做大规模重构**。阻断问题交 ChatGPT 设计修复，再由豆包应用与测试。

## 1. 已核对正常的部分

| 项 | 文件 | 核对结果 |
| --- | --- | --- |
| 后端令牌校验 | `backend/main.py` | 无/错令牌 401，正确令牌 200（TASK-002.1 实测） |
| CORS 白名单 | `backend/main.py` | 放行 127.0.0.1:1420 / localhost:1420 等；未授权 Origin 无 allow-origin |
| SQLite 初始化 | `backend/main.py` | 两表创建，schema_version=1，重复初始化保留版本 |
| root 只读 | `backend/main.py`、`frontend/src/App.tsx` | 修改 root 返回 400；前端保存前剔除只读 root，输入框 readOnly |
| 数据根默认值 | `backend/main.py`、`frontend/src-tauri/src/lib.rs` | 两端默认根均为 `%LOCALAPPDATA%\ComfyUI-Prompt-Workbench`，已统一 |
| 日志分流 | `frontend/src-tauri/src/lib.rs` | stdout/stderr 写数据根 logs；令牌仅经环境变量，不入日志 |
| 退出清理 | `frontend/src-tauri/src/lib.rs` | 只 kill 自己的 child；未按进程名批量结束外部服务 |
| 忽略规则 | `.gitignore` | `.venv/`、`node_modules/`、`dist/`、`target/`、`gen/`、`*.log`、`data/`、`workbench-data/` 均被忽略 |

## 2. 发现的问题与待改进项

### 2.1 sidecar 仍按开发方式查找 Python（打包前必须改）

- 文件：`frontend/src-tauri/src/lib.rs`（`find_python`）
- 现状：优先 `WORKBENCH_PYTHON`，其次项目 `.venv\Scripts\python.exe`，再回退系统 `python`。
- 影响：开发阶段可用；正式安装包内既无 `.venv` 也无系统 Python，该查找逻辑会失败。
- 复现条件：在未安装 Python 的干净 Windows 上运行打包后的 Tauri 程序。
- 建议方向（交 ChatGPT 设计）：生产模式启动 PyInstaller 生成的 sidecar 可执行文件，不再查找 Python 解释器；区分开发/生产启动路径。
- 状态：未修改，属打包阶段阻断项之一。

### 2.2 Tauri 打包配置未启用

- 文件：`frontend/src-tauri/tauri.conf.json`
- 现状：`bundle.active = false`；未配置图标、sidecar/externalBin、NSIS 安装选项、签名。
- 影响：当前无法直接产出可分发安装包；不影响开发期前后端联调。
- 复现条件：在具备 Rust/MSVC 的环境执行 `tauri build`。
- 建议方向：打包实现阶段补齐 bundle、图标、externalBin 与 NSIS 配置。
- 状态：未修改。

### 2.3 版本号两处不一致

- 文件：`frontend/src-tauri/tauri.conf.json`（0.1.0）、`backend/main.py`（`APP_VERSION = 0.1.0-dev.2`）
- 现状：前端/打包清单为 0.1.0，后端为 0.1.0-dev.2。
- 影响：发布版本对齐时可能出现版本展示不一致；当前开发阶段不阻塞功能。
- 复现条件：查看 Tauri 应用版本与后端 `/api/health` 返回版本。
- 建议方向：确定开发/发布版本号规则，统一来源。
- 状态：未修改。

### 2.4 CSP 当前为空

- 文件：`frontend/src-tauri/tauri.conf.json`（`app.security.csp = null`）
- 现状：未配置内容安全策略。
- 影响：Tauri 安全基线建议设置 CSP 限制资源来源；当前界面为本地静态资源 + loopback API，风险有限，但收紧 CSP 属后续安全阶段事项。
- 建议方向：后续阶段按 Tauri 2 安全指南补 CSP；不在本任务范围。
- 状态：未修改。

### 2.5 后端含 pytest 等开发依赖

- 文件：`backend/requirements.txt`
- 现状：`pytest>=8.3,<9` 列在后端 requirements；`.venv` 实测含 pytest、pluggy、iniconfig、Pygments 等测试包。
- 影响：PyInstaller 打包若直接引用全部依赖，会把测试工具带入 sidecar，增大体积。
- 建议方向：运行依赖与测试依赖拆分（如 `requirements.txt` + `requirements-dev.txt`），打包只收集运行依赖。
- 状态：未修改。

### 2.6 仓库内无 logs 目录属预期，记录备查

- 现状：仓库内 `backend/logs/` 不存在；运行日志写在用户数据根 `logs/`。
- 影响：无；仅避免后续误判为“缺少日志目录”。
- 状态：无需修改。

## 3. 未在本次审查中运行的验证

- Rust `cargo check` / `tauri build`：本机无 Rust/MSVC，未执行。
- PyInstaller 打包：未配置、未执行。
- 桌面端到端：未在 Tauri 壳内运行。
- 后端本次未重启；后端可运行性依据 TASK-002.1 实测记录。

## 4. 阻断与非阻断归类

| 编号 | 问题 | 类别 | 责任分工 |
| --- | --- | --- | --- |
| 2.1 | sidecar 查找 Python 逻辑不适用于打包产物 | 打包阻断（打包前必须解决） | ChatGPT 设计修复，豆包后续实测 |
| 2.2 | Tauri bundle/NSIS/sidecar 配置未启用 | 打包阻断（打包阶段实现） | ChatGPT 设计，豆包后续构建验收 |
| 2.3 | 版本号两处不一致 | 待对齐（非功能阻断） | ChatGPT 定规则，豆包核对 |
| 2.4 | CSP 未配置 | 后续安全阶段事项 | 后续阶段处理 |
| 2.5 | 测试依赖混入后端依赖清单 | 打包体积优化项 | ChatGPT 调整依赖拆分 |
