# ADR-0001：Windows 桌面技术栈（已废弃 · 历史记录）

-   状态：**已废弃（2026-11-18）**，被 ADR-0002《本机浏览器 Web 运行时（免安装）》取代；下文 Tauri 2 / PyInstaller / NSIS / Rust 工具链相关内容仅作历史决策记录，**不再作为当前实现或验收依据**。
-   日期：2026-11-17
-   决策范围：第一版 Windows 桌面应用与本地业务服务（旧口径）

## 背景

产品需要现代化复杂 UI，但又必须可靠访问本地文件、管理本地 LLM
模型状态、读取 GPU 显存、连接 ComfyUI HTTP/WebSocket、使用
SQLite，并最终交付可双击启动的 Windows EXE。

用户设备为 Windows 11、16GB RAM、RTX 4060 Laptop 8GB
VRAM。项目需要长期维护，并允许不同智能体接手。

## 推荐决策

-   Tauri 2.x：桌面窗口与系统集成。
-   React + TypeScript + Vite：前端 UI。
-   Python 3.12 起步 + FastAPI：本地业务服务。
-   PyInstaller：将 Python 服务打包为 Windows sidecar。
-   SQLite：本地数据存储。
-   Ollama adapter：第一版本地 LLM 运行时。
-   ComfyUI HTTP + WebSocket adapter：工作流任务集成。
-   Tauri NSIS Windows setup EXE：第一版安装包。

采用模块化单体。Python 是业务逻辑权威层；Rust/Tauri
只负责桌面宿主；React 只负责界面。

## 选择理由

### Tauri 而不是 Electron

Electron 将 Chromium 和 Node.js
一起嵌入应用，开发体验成熟，但桌面运行时会携带完整浏览器运行环境。

Tauri 在 Windows 使用 WebView2 系统运行时，通常可复用 Windows 11
已安装的 Edge WebView2，应用包不需要重复携带完整
Chromium。对本地单机工具更有吸引力。

代价：Tauri 需要 Rust、Windows C++ Build Tools、Node.js 和 WebView2
开发依赖；sidecar 启动、权限、打包需要专门测试。该复杂度通过把 Rust
层保持薄、将业务逻辑集中在 Python 来控制。

### React + TypeScript + Vite

Prompt 编辑器涉及结构化区块、拖放、候选差异、历史和复杂交互。React
组件生态和 TypeScript 类型约束适合该复杂度。前端不承担安全边界判断。

### Python + FastAPI sidecar

ComfyUI 和 Ollama 都提供本地 HTTP 接口；ComfyUI 还提供 WebSocket
事件。Python 生态适合 JSON 解析、HTTP/WebSocket、SQLite
和本地进程/显存检查。将服务独立打包后，用户不必为了运行软件安装匹配版本的
Python。

工作台使用自己的 Python 运行时，不复用 ComfyUI 秋叶整合包中的
Python，以避免与 ComfyUI 的 PyTorch/CUDA/自定义节点依赖冲突。

### SQLite

第一版为单用户本地桌面应用，无需独立数据库服务。SQLite
可保存模型身份、规则版本、草稿、历史、队列和设置；备份/恢复也更容易实现。图片原件和模型权重仍留在用户目录。

## 暂不采用的方案

-   纯浏览器 Web
    应用：不是用户期望的最终交付体验；需要额外启动本地服务和浏览器。
-   Electron + React：可行且生态成熟，但携带完整 Chromium/Node runtime
    的开销对本项目未必必要。
-   纯 Python 桌面 UI：Python 集成自然，但复杂 Prompt 编辑器和网页 UI
    生态的灵活性较低。
-   Tauri + Rust 实现全部业务：不采用。项目 JSON、ComfyUI、Ollama
    和模型资料逻辑更适合集中在 Python。
-   微服务：不采用。单用户本地桌面工具拆微服务会增加部署、通信和维护成本。

## M0 必须验证的事项

1.  Tauri 能否在 Windows 11 稳定启动 Python sidecar。
2.  sidecar 能否安全地绑定 loopback，并通过随机端口/会话 token 握手。
3.  PyInstaller 打包后的服务能否正常运行，启动耗时是否可接受。
4.  Tauri 安装程序能否正确携带 sidecar 并启动。
5.  应用退出时能否只结束自己的 sidecar，不影响 ComfyUI/Ollama。
6.  Windows WebView2 缺失/版本不符时的提示或安装器处理方式。
7.  杀毒误报、崩溃诊断、onefile/onedir 打包方式的权衡。

## 风险与缓解

  ---------------------------------------------------------------------------------------
  风险                                缓解
  ----------------------------------- ---------------------------------------------------
  Tauri sidecar 启动失败              独立健康检查、启动超时、日志、开发/生产一致性测试

  本地 API 被其他网页访问             loopback 绑定、随机端口、随机 token、Origin/CORS
                                      校验

  Python 依赖冲突                     独立 venv/打包运行时，不复用 ComfyUI Python

  PyInstaller 打包差异                CI 构建、Windows smoke test、先验证 onedir 再评估
                                      onefile

  WebView2 缺失/版本过旧              Windows 安装器配置 WebView2 检查/引导

  LLM 显存释放无法确认                多信号验证；状态 unknown 时禁止出图

  UI 与后端业务规则重复               后端为唯一权威，前端只显示服务返回结果
  ---------------------------------------------------------------------------------------

## 官方参考（实现前核验最新内容）

-   Tauri 文档：https://v2.tauri.app/
-   Tauri Windows 前置要求：https://v2.tauri.app/start/prerequisites/
-   Tauri sidecar：https://v2.tauri.app/develop/sidecar/
-   Tauri Windows
    安装程序：https://v2.tauri.app/distribute/windows-installer/
-   Electron 文档：https://www.electronjs.org/docs/latest/
-   React 文档：https://react.dev/
-   PyInstaller 文档：https://pyinstaller.org/en/stable/
-   ComfyUI
    服务通信文档：https://github.com/Comfy-Org/docs/blob/main/development/comfyui-server/comms_routes.mdx

## 重新评估条件

只有在以下情况才重新打开此 ADR： - Tauri sidecar 无法稳定打包/运行
Python 服务。 - Windows WebView2 兼容性造成无法接受的问题。 -
用户明确要求跨平台优先于 Windows。 -
性能测量证明当前架构无法满足目标设备。 -
经过真实原型验证，其他技术方案显著降低长期维护成本。

重新评估必须提供原型数据和迁移成本，不因个人偏好更换技术栈。
