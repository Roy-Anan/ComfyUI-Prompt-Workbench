# 架构变更报告 — TASK-002.3

- 日期：2026-11-17
- 变更性质：运行形态从 Tauri 桌面壳切换为本机浏览器 Web 应用；业务逻辑、数据层与安全约束沿用既有设计。

## 1. 变更前（历史基线，已取消）

- 宿主：Tauri 2.x / Rust 桌面窗口，sidecar 拉起 Python 服务，经 Tauri 命令获取随机端口与会话令牌。
- 前端：React + TS + Vite，经 `@tauri-apps/api/core` 的 `invoke` 与宿主通信。
- 打包规划：PyInstaller sidecar + Tauri externalBin + NSIS/EXE。
- 取消原因：本机缺 Rust/MSVC 工具链，桌面闭环无法在本机编译运行；经任务书决策正式停止该方向投入。

## 2. 变更后（当前 Web 基线）

- 单一 Python 进程（FastAPI）：同时提供 `/api/*` 与前端静态产物 `frontend/dist/`。
- 前端：React + TS + Vite 仅负责构建静态产物；运行时经同源相对路径 fetch 调用后端，不再调用宿主命令。
- 访问入口：本机浏览器打开 `http://127.0.0.1:8000`；可由 `WORKBENCH_HOST` / `WORKBENCH_PORT` 配置，非 loopback 绑定在启动时被拒绝。
- 进程生命周期：`.bat` 入口调用 Python 启动/停止脚本；启动器写 `.workbench.pid`（运行时文件，已加入 `.gitignore`）；停止器按 PID 终止工作台进程树。

## 3. 会话与安全调整

- 新增 `GET /api/bootstrap`：对无 Origin 或回环白名单 Origin 的同源浏览器请求签发会话票据（HttpOnly Cookie `workbench_session`）与 CSRF 令牌（Cookie `workbench_csrf`，响应体回传 `csrf`）。
- 认证中间件区分两类会话：Cookie 票据会话、Bearer 引导令牌会话。
- 状态变更（非安全方法）对 Cookie 会话校验 `X-Workbench-CSRF` 头；Bearer 会话豁免 CSRF（用于脚本/CLI/测试）。
- Origin 白名单校验；外部 Origin 的 bootstrap 必须携带 Bearer 引导令牌；引导令牌仅经环境变量 `WORKBENCH_SESSION_TOKEN` 传递，不写入前端构建文件。
- 静态资源与 SPA 壳不经 API 认证；API 与静态兜底路由分离：`/api/` 前缀未命中返回 JSON 404，不返回 HTML。

## 4. 静态托管与兜底行为

- `dist/` 存在：正常返回静态资源；深层非 API 路由回退 `index.html`。
- `dist/` 缺失：返回 503 与明确错误信息。
- 路径越出 dist：返回 403。
- `/api/` 未命中：返回 JSON 404。

## 5. 保留不变的部分

- SQLite 初始化与版本管理、数据根 `%LOCALAPPDATA%\ComfyUI-Prompt-Workbench`。
- 设置管理 API、目录初始化、Checkpoint/LoRA 外部目录校验、Ollama/ComfyUI 连接配置与只读检测。
- 损坏 `settings.json` 先备份再重建的机制。
- API 认证未关闭；loopback 安全边界未放开到局域网/公网。

## 6. 前端构建与运行路径差异

- 开发模式（Vite dev server，历史 1420/1420 端口口径）仅用于前端独立调试；正式 Web 运行不启动 Node 开发服务器，浏览器直连 FastAPI 同源 8000 端口。
- 本次交付的正式运行产物为 `frontend/dist/`，由 FastAPI 托管。

## 7. 归档处置

- 原 `frontend/src-tauri/`（Cargo.toml、build.rs、tauri.conf.json、capabilities/default.json、src/main.rs、src/lib.rs）整体移动到 `legacy/src-tauri/`，内容保留未删除。
- `legacy/README.md` 说明该目录为历史方案归档，不属于 Web 运行时。
- `package.json` 移除 `@tauri-apps/api` 运行依赖、`@tauri-apps/cli` devDependency 与 `tauri` script；`package-lock.json` 已随 `npm install` 刷新。
