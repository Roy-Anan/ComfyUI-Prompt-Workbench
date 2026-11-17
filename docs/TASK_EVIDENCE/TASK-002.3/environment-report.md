# 环境报告 — TASK-002.3

- 采集日期：2026-11-17
- 采集方式：本机只读命令采集，未安装开发工具，未修改系统 PATH/注册表/防火墙/杀毒设置。
- 原始输出：`logs/environment-versions.txt`、`logs/environment-data-check.txt`。

## 1. 操作系统

| 项 | 实测值 |
| --- | --- |
| 系统 | Microsoft Windows 11 家庭版 中文版 |
| 版本 | 10.0.26200（64 位） |
| 用户权限 | 非管理员（沿用 TASK-002.2 盘点结论） |

## 2. 运行时与依赖（项目 `.venv`）

| 项 | 实测值 |
| --- | --- |
| Python | 3.13.18（项目 `.venv`） |
| pytest | 8.4.2 |
| FastAPI | 0.163.1 |
| Uvicorn | 0.54.0 |
| httpx | 0.28.1 |
| Pydantic | 2.14.3 |
| Node | v22.23.2（仅前端构建用） |
| npm | 10.9.8 |
| Vite | 5.4.21（前端构建） |

## 3. 数据根（实测）

- 数据根：`C:\Users\15380\AppData\Local\ComfyUI-Prompt-Workbench`（即 `%LOCALAPPDATA%\ComfyUI-Prompt-Workbench`）。
- 内容：
  - `settings.json`（1139 字节）
  - `database\workbench.sqlite3`（16384 字节）
- SQLite：表 `app_metadata`、`schema_version`；`schema_version = 1`。
- 数据目录不在前端构建目录或安装目录内。

## 4. 环境限制与说明

- 本机未安装 Python 3.12；后端测试在 Python 3.13.18 下通过，3.12 兼容性未单独验证。
- 本机缺 Rust 工具链与 MSVC C++ Build Tools；Tauri 桌面方向已在本任务取消，不再补装。
- 正式运行不要求 Node 开发服务器；Node/Vite 仅在构建前端静态产物时使用，运行时由 FastAPI 托管 `dist/`。
- 沿用 TASK-002.2 采集的 WebView2 / Edge / VC++ 记录（见 `docs/TASK_EVIDENCE/TASK-002.2/raw-outputs/`）；本次未重复安装或升级系统组件。
