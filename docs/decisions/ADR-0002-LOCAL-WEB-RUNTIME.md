# ADR-0002：本机浏览器 Web 运行时（免安装）

- 状态：已采纳（当前正式运行形态）
- 日期：2026-11-18
- 决策范围：第一版本地交付形态、运行入口、技术栈取舍
- 取代：ADR-0001（Tauri 2 + PyInstaller sidecar + NSIS EXE，已废弃，仅作历史记录）

## 背景

ADR-0001 原计划用 Tauri 2 桌面窗口承载 Python FastAPI sidecar，并用 PyInstaller 打包、NSIS 出 Windows 安装包。实际推进中发现：

- 本机缺少 Rust 工具链与 MSVC C++ Build Tools，Tauri 编译、sidecar 拉起、安装包打包链路在当前设备上无法闭环验证。
- 项目是单用户、单机、本地工具，核心价值是工作流安全保护、Prompt 创作与本地服务协调，并不依赖独立桌面窗口外壳。
- 引入打包链会带来 WebView2 兼容、代码签名、升级覆盖、杀毒误报等额外维护成本，与「便捷、不易出错、好维护」的目标冲突。

## 推荐决策

- **运行形态**：本机浏览器 Web 应用。FastAPI 同时托管前端静态产物（`frontend/dist/`）与 `/api/*`，同源相对路径访问。
- **访问地址**：默认 `http://127.0.0.1:17890`（`WORKBENCH_HOST` / `WORKBENCH_PORT` 可配置；非回环绑定在启动时被拒绝）。选用 17890 是为避开本机已部署的酒馆（SillyTavern，原 8000 端口）及其他本地服务。
- **技术栈**：React + TypeScript + Vite（前端）；Python + FastAPI（后端业务权威）；SQLite（本地结构化数据）；Ollama Adapter、ComfyUI HTTP/WebSocket Adapter。模块化单体，不拆微服务。
- **交付方式**：免安装。双击 `启动工作台.bat` 启动服务并打开浏览器，`停止工作台.bat` 停止服务；不产出 EXE / NSIS 安装包。
- **运行依赖**：正式运行只需项目 `.venv` 中的 Python 依赖；Node/Vite 仅在构建前端产物时使用，正式运行不启动 Node 开发服务器。

## 选择理由

### 为什么放弃 Tauri/PyInstaller/NSIS

- 绕开 Rust/MSVC 工具链依赖，消除历史最大的编译与打包阻塞。
- 没有安装包、签名、WebView2 引导、升级覆盖等维护负担。
- 改后端重启服务即可生效；改前端重新 `vite build` 即可，迭代链路短。
- 浏览器本身已是成熟渲染层，回环访问对单用户本地工具足够。

### 为什么仍保留 FastAPI 后端

- 工作流白名单、非白名单校验、规则继承、队列状态、显存安全判定等安全边界必须由程序在后端强制执行；前端只展示与发起命令，不承担安全判断。
- Python 生态处理 ComfyUI/Ollama HTTP 与 WebSocket、JSON 解析、SQLite、本地进程与显存检查更直接。

## 明确不做

- 不开发 Tauri/Rust 桌面宿主；`legacy/src-tauri/` 历史代码归档保留，不参与 Web 运行时。
- 不做 PyInstaller sidecar 打包与 NSIS/EXE 安装包。
- 不监听 `0.0.0.0`，不开放局域网/公网访问。
- 不接云端 AI API，不要求用户配置云端 API Key，不自动上传用户内容。

## 风险与缓解

| 风险 | 缓解 |
| --- | --- |
| 本地 API 被其他网页访问 | 仅绑定 127.0.0.1；进程内会话票据 + CSRF 头；Origin 白名单校验 |
| 端口与本机其他服务冲突 | 默认端口 17890，可经 `WORKBENCH_PORT` 覆盖；启动前做身份校验与占用检查 |
| 前端产物过期 | 交付前执行 `tsc -b && vite build`；`dist/` 不入库，由构建生成 |
| 浏览器关闭后服务仍在后台 | 由停止器按 PID + 进程身份记录回收工作台进程树，不按名称批量结束 Python |

## 重新评估条件

只有出现以下情况才重新打开本决策：

- 用户明确要求独立桌面窗口外壳或正式安装包分发。
- 浏览器同源方案在本机出现无法解决的兼容性问题。
- 真机测量证明当前架构无法满足目标设备（16GB RAM / RTX 4060 Laptop 8GB）。

重新评估必须提供原型数据与迁移成本，不因个人偏好更换技术栈。
