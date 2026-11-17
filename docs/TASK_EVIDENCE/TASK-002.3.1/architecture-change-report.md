# 架构变更报告 — TASK-002.3.1

## 1. 变更定位

本次不改变 TASK-002.3 确立的本机 Web 拓扑，只在其上调整数据目录归属与运行时安全边界：

```text
本机浏览器 (Edge/Chrome)
  └─ 同源 loopback：FastAPI 同时托管 frontend/dist 与 /api/*
       ├─ 认证：bootstrap 票据 + CSRF；/api/health 为未认证身份探测
       ├─ 静态托管：真实路径包含判断，拒绝穿越与前缀碰撞
       ├─ 数据层：SQLite + 本地文件，根目录固定为项目内 userdata/
       └─ 外部适配：Ollama / ComfyUI 仅连通性检测，不自启自关
```

## 2. 数据目录归属调整

- **调整前**：默认数据根为 `%LOCALAPPDATA%\ComfyUI-Prompt-Workbench`（用户漫游目录，与源码分离但不在项目内）。
- **调整后**：默认数据根为仓库内 `userdata/`，可由 `WORKBENCH_DATA_ROOT` 覆盖；`userdata/` 被 Git 忽略，运行时用户数据与源码隔离、不入库。
- **保留原则**：模型权重、原图、原始工作流仍在 ComfyUI 原有外部目录，工作台只记录路径与索引；不复制进 `userdata/`。
- **迁移安全**：旧根保留；迁入前在新根 `backups/` 备份；SQLite 做完整性校验；新根已有数据时不覆盖。

## 3. 安全边界调整

| 边界 | 调整前 | 调整后 |
| --- | --- | --- |
| 监听地址 | 启动器未前置校验回环 | 启动前拒绝非 loopback 地址 |
| 进程识别 | 停止器主要依赖 PID | 可执行路径 + 命令行 + 启动时间多重核验，fail-closed |
| 进程回收 | 按 PID 结束 | 递归回收整棵进程树，不按名称批量杀 Python |
| 静态路径 | 字符串前缀匹配 | 解码后真实路径包含判断，拒绝穿越与相邻前缀碰撞 |
| 健康检查 | 被认证拦截 401；就绪判定弱 | 未认证身份探测，响应体携带应用标识，启动器据此核验 |

## 4. 模块职责变化

- 新增 `backend/datadir.py`：统一数据根识别、子目录规划、迁移备份与完整性校验；`main.py` 不再自行拼接数据路径。
- `backend/main.py`：接入 datadir；提供 loopback 校验函数、真实路径解析、健康身份标识；中间件放行健康探测。
- `scripts/workbench_launcher.py`：loopback 前置校验、健康身份核验、端口占用区分实例。
- `scripts/workbench_stopper.py`：CIM 身份核验、递归进程树、不匹配保留现场。

## 5. 未改变的部分

- FastAPI 业务逻辑权威实现、React 前端、SQLite 结构化数据、会话票据与 CSRF、Origin 白名单、Ollama/ComfyUI 适配边界均沿用 TASK-002.3。
- 历史 Tauri/Rust 工程仍归档于 `legacy/src-tauri/`，不参与 Web 运行时；本次未重新引入 Rust/EXE 构建。
