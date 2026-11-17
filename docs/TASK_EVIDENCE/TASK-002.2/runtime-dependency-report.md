# 运行依赖报告 — 开发依赖 ≠ 用户运行依赖

- 采集时间：2026-11-17 21:59（UTC+8）
- 适用对象：最终拿到 Windows EXE 安装包的普通用户；不是开发人员

## 1. 核心原则

- **开发工具只在打包机器上需要**，最终用户机器不应被要求安装 Rust、MSVC、Node.js、npm、Python 解释器或运行 Python 命令。
- **运行组件随安装包或系统提供**：桌面运行时（WebView2）、必要的 C/C++ 运行时、打包后的 Python sidecar 与前端静态资源。
- 安装包**不携带** ComfyUI 模型权重（Checkpoint / LoRA / 大模型），**不依赖**秋叶整合包的 Python，**不要求**用户自行配置开发环境。

## 2. 最终用户运行组件（目标态，待打包后实测核对）

| 组件 | 角色 | 来源 | 现状 / 说明 |
| --- | --- | --- | --- |
| Windows 10/11 x64 系统 | 运行环境 | 用户系统 | 本机为 Windows 11 家庭版 26200 x64 |
| WebView2 Runtime | Tauri 2 桌面界面渲染载体 | 系统预装或随包提供 Evergreen Runtime | 本机已装 157.0.4341.46；Tauri 壳内实际可用性待真机验证 |
| VC++ Runtime（x64，必要时含 x86） | Rust 二进制 / PyInstaller 后端链接的 C 运行时 | 随安装包捆绑或系统已有 | 本机已检测到 v14 2022 / 14.51 x64+x86；最终是否捆绑以打包产物链接情况为准 |
| 打包后的 Tauri 桌面程序（EXE） | 主程序 | 安装包内 | 尚未构建（缺 Rust/MSVC 构建环境） |
| PyInstaller 打包的 Python sidecar | 后端 API 进程 | 安装包内，由 Tauri 拉起 | 尚未打包；最终用户机器不需要装 Python |
| 前端静态资源（React + Vite 产物） | 界面文件 | 嵌入 Tauri 或随包分发 | 现有 `dist/` 约 0.1 MB |
| SQLite（运行库） | 本地元数据存储 | 由 Python 依赖 / sidecar 自带 | 标准库 `sqlite3`，无需用户单独安装 |

## 3. 可以随安装包一起提供的组件

- PyInstaller 打包后的后端 sidecar（含其第三方 Python 依赖：FastAPI、Uvicorn、httpx、Pydantic、Starlette 等）。
- 前端静态资源与 Tauri 主程序。
- 如打包产物检测到缺少 VC++ Runtime，可在 NSIS 安装流程中静默安装对应可再发行包（具体策略由打包设计确定）。
- WebView2 Evergreen Bootstrapper / Fixed Version：若目标机器未装 WebView2，可由安装包引导安装；本机已具备。

## 4. Windows 通常已有的系统组件

- 基础 Win32 / 网络栈（loopback、TCP/IP）。
- 多数 Win11 机器已自带 WebView2 Runtime；老旧 Win10 可能缺失，需在安装包中处理。
- 部分机器已装有 VC++ Runtime；版本是否满足产物链接要求需打包后核对。

## 5. 缺失才需要单独安装的组件

- **WebView2 Runtime**：仅在目标机器未安装时需要（Evergreen 在线安装或随包 Fixed Version）。
- **VC++ Redistributable**：仅当打包产物在干净系统上提示缺少运行时 DLL 时需要捆绑安装。
- 除此之外，最终用户**不应**被要求安装 Python、Node、Rust、MSVC 或任何 SDK。

## 6. 最终用户完全不需要安装的开发工具

| 开发工具 | 为什么用户不需要 |
| --- | --- |
| Rust / rustup / Cargo | 仅用于在打包机器编译 Tauri 主程序；产物为原生 EXE，用户侧不编译 |
| MSVC / Visual Studio / Windows SDK | 仅链接期需要；用户侧不做 C/C++ 编译 |
| Node.js / npm / Vite / TypeScript | 仅用于构建前端；产物为静态文件，用户侧不跑构建 |
| Python 解释器 / pip / venv | 后端由 PyInstaller 打成独立 sidecar；用户侧不运行 Python 命令、不建虚拟环境 |
| 秋叶 ComfyUI 整合包及其 Python | 安装包不依赖整合包环境；ComfyUI / Ollama 是用户自行管理的外部服务 |

## 7. 外部服务依赖（不属于安装包组件）

- **ComfyUI**：用户本机独立运行的外部服务，工作台仅通过 `http://127.0.0.1:8188` 检测与对接；安装包不携带 ComfyUI 本体与模型。
- **Ollama**：用户本机独立运行的外部 LLM 服务，工作台仅通过 `http://127.0.0.1:11434` 检测；安装包不携带 Ollama 与模型权重。
- 本次代码对 ComfyUI / Ollama 只做连通性检测，不自动启动、关闭或重启它们。

## 8. 待打包阶段确认的依赖结论

1. PyInstaller 后端在干净 Win11 x64 上的 DLL 依赖清单（用实际产物 `--collect` / 依赖扫描核对）。
2. Tauri Rust 二进制最终链接的 VC++ 版本与位数（x64；是否需 x86）。
3. WebView2 在 Evergreen 与 Fixed Version 两种策略下的体积与离线可用性。
4. sidecar 作为 Tauri external binary 的命名、目录与权限约定。
