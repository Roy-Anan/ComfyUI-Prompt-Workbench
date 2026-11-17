# 环境报告 — Windows 用户运行环境现状

- 采集时间：2026-11-17 21:59（UTC+8）
- 采集方式：只读；原始输出见 `raw-outputs/env-windows-runtime.txt`、`raw-outputs/disk-space.txt`

## 1. Windows 基本信息

| 项目 | 实测值 |
| --- | --- |
| 系统 | Microsoft Windows 11 家庭版 中文版 |
| 版本 / 内部版本号 | 10.0.26200（Build 26200） |
| 系统架构 | 64 位（AMD64 / x64） |
| 区域 | 0804（中文） |
| CPU | Intel64 Family 6 Model 154 Stepping 3, GenuineIntel |
| 当前用户 | ROY\15380 |
| 是否管理员 | **否**（IsAdmin=False） |

说明：当前进程以非管理员身份运行。正式安装包若采用每用户安装（per-user）通常不需要管理员权限；若要做全机器安装或写入 `Program Files`，才需要提权。该选型待打包设计阶段确定。

## 2. 磁盘空间（采集时点快照）

| 盘符 | 可用空间 | 总容量 | 已用 |
| --- | --- | --- | --- |
| C: | 45.95 GB（47055.1 MB） | 152.79 GB | — |
| D: | 49.11 GB（50288.5 MB） | 323.20 GB | 274.1 GB |

- 项目仓库位于 **D 盘**：`D:\AI\ComfyUI-Prompt-Workbench-Git`，D 盘剩余约 49.11 GB。
- 用户默认数据目录位于 **C 盘** `%LOCALAPPDATA%\ComfyUI-Prompt-Workbench`（当前尚不存在，首次启动后由后端创建）。
- 磁盘数值为采集时点快照，会随系统与其他软件变化。

## 3. WebView2 Runtime

| 项目 | 实测值 |
| --- | --- |
| WebView2 Runtime 安装 | **已安装**（注册表 `HKLM\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}` 存在） |
| Runtime 版本 | 157.0.4341.46 |
| Runtime 安装位置 | `C:\Program Files (x86)\Microsoft\EdgeWebView\Application` |
| Edge 浏览器版本 | 157.0.4341.60（`C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`） |
| 系统是否识别 | 注册表 `pv` 与 `location` 字段可读，系统可识别该 Runtime |

说明：Edge 浏览器已安装不等于 WebView2 Runtime 一定可用；本次在 Runtime 专属注册表项读到了版本与安装路径，按注册表口径判定为已安装。WebView2 在 Tauri 壳内的实际渲染仍需在具备 Tauri 构建环境后真机验证。

## 4. VC++ Redistributable（本机现状，非最终依赖结论）

已检测到以下已安装项（注册表卸载项读取）：

- Microsoft Visual C++ 2022 Redistributable (x64) 14.38.33135.0
- Microsoft Visual C++ v14 Redistributable (x64) 14.51.36247.0
- Microsoft Visual C++ v14 Redistributable (x86) 14.51.36247.0

说明：这是本机当前状态。最终 EXE 是否必须捆绑 VC++ Runtime，取决于 Tauri Rust 二进制与 PyInstaller 打包后后端所链接的运行时，需在打包阶段用实际产物核对（见 `installer-design-report.md`）。

## 5. Python 运行环境

### 5.1 系统 Python

| 解释器 | 版本 | 路径 |
| --- | --- | --- |
| `python`（PATH） | 3.13.18 | 由 PATH 解析（采集进程沙箱 Python 3.13.18） |
| `python3` | 未找到（rc=9009） | — |
| `py` 启动器 | 3.9.10 | `py -0p` 列出 3.9-64、3.9-32 |
| Python 3.12 | **未安装** | — |

`py -0p` 实际列出：

- 3.9-64 → `C:\Program Files\Python39\python.exe`
- 3.9-32 → `C:\Program Files (x86)\Python39-32\python.exe`

### 5.2 项目虚拟环境 `.venv`

| 项目 | 实测值 |
| --- | --- |
| 路径 | `D:\AI\ComfyUI-Prompt-Workbench-Git\.venv\Scripts\python.exe` |
| 是否存在 | 是 |
| 版本 | 3.13.18（Windows-11-10.0.26200-SP0） |

### 5.3 后端依赖（`backend/requirements.txt`）

```text
fastapi>=0.115,<1
uvicorn[standard]>=0.34,<1
httpx>=0.28,<1
pydantic>=2.10,<3
pytest>=8.3,<9
```

`.venv` 已安装的关键包（`pip list` 实测）：fastapi 0.163.1、uvicorn 0.54.0、httpx 0.28.1、pydantic 2.14.3、starlette 1.10.0、pytest 8.4.2、anyio 4.16.0、h11 0.16.0、httptools 0.9.0、websockets 17.4、watchfiles 1.3.0、PyYAML 6.0.3、python-dotenv 1.2.4、certifi 2026.10.23 等。

### 5.4 后端在现有环境中的可运行性

- 后端入口 `backend/main.py` 存在；测试 `backend/test_main.py` 存在。
- TASK-002.1 已在该 `.venv` 完成：`py_compile` 退出码 0；pytest 13 项通过；真实 HTTP 冒烟在临时数据根下跑通（401/200、CORS、SQLite、损坏配置备份等）。证据见 `PROJECT_STATE.md` 与 `PROJECT_CHANGELOG.md`。
- 本次任务**未重新启动后端**（避免与既有状态混淆）；可运行性以上一轮实测记录为准。
- 正式 EXE 计划：Python 后端后续通过 **PyInstaller 打包为独立 sidecar**，最终用户**不需要自行安装 Python 或运行 Python 命令**（方案见 `installer-design-report.md`，当前尚未实现）。

## 6. 开发工具现状（本机缺失，仅记录，不安装）

| 工具 | 现状 |
| --- | --- |
| Rust（rustc / cargo / rustup） | 均未找到；`~/.cargo`、`~/.rustup` 不存在 |
| MSVC / Visual Studio | `cl.exe`、`link.exe` 未找到；`vswhere.exe` 不存在；`Program Files\Microsoft Visual Studio` 等目录不存在 |
| Node.js / npm | 前端 `node_modules` 与 `dist` 为 TASK-002/002.1 既有产物；本次未重新安装 Node |
| Python 3.12 | 未安装 |

当前机器未具备桌面开发构建环境，本任务不安装该环境。

## 7. 项目产物与目录现状

| 检查项 | 现状 |
| --- | --- |
| 前端构建产物 `frontend/dist/` | 存在（index.html 0.41 KB、JS 148589 B、CSS 2771 B，合计约 0.1 MB） |
| `frontend/node_modules/` | 存在（约 79.4 MB，被 `.gitignore` 忽略，不入库） |
| Tauri 配置 `tauri.conf.json` | 存在 |
| Rust 清单 `Cargo.toml` | 存在 |
| Sidecar 启动代码 `src/lib.rs` | 存在 |
| 后端入口 `main.py` | 存在 |
| 仓库内 `logs/` 目录 | 不存在（运行时日志写在用户数据根 `logs/`，不在仓库内） |
| 默认数据目录 | `%LOCALAPPDATA%\ComfyUI-Prompt-Workbench`，当前不存在，首次启动后创建 |
| 当前程序能否在现有环境直接运行桌面端 | **不能**：缺 Rust/MSVC 构建环境，Tauri 桌面程序无法编译；后端可在 `.venv` 运行，前端静态构建已通过 |
