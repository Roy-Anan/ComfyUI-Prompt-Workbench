# legacy/ — 历史方案归档

本目录存放早期 Tauri 桌面方向遗留的工程文件，**不属于当前本地 Web 运行时**，
前端构建、后端启动、浏览器访问均不引用本目录。

## src-tauri/

- 来源：TASK-002 阶段搭建的 Tauri 2 + Rust 桌面壳工程。
- 状态：方向已在 TASK-002.3 正式切换为本机浏览器 Web 应用，Tauri/Rust/Cargo/MSVC
  不再作为运行依赖，也不再为其补充工具链或开发新功能。
- 保留原因：保留历史决策与代码线索，便于回溯；其中的 `Cargo.toml`、`tauri.conf.json`、
  Rust 入口等仅作归档参考，请勿在 Web 运行时中调用。
- 运行影响：当前 `backend/`（FastAPI）与 `frontend/`（React + Vite）均不依赖本目录。

## 处置边界

- 本目录内容不参与 `npm run build`、不参与后端启动脚本。
- 后续如确认不再需要历史桌面壳，可在单独任务中评估删除；当前阶段仅归档、不删除。
