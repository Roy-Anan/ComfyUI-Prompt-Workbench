# TASK-002.3 证据目录 — 切换本机 Web 架构并完成一键启动基础

- 任务编号：TASK-002.3
- 记录日期：2026-11-17
- 开发分支：`dev`（不合并 main）
- 版本：`0.1.0-dev.3`
- 执行人：豆包

## 1. 任务边界

将项目从 Tauri 桌面方向切换为本机浏览器 Web 应用：FastAPI 托管 React 前端静态产物并提供同源 API，浏览器访问 `http://127.0.0.1:8000`；保留 SQLite、设置/数据目录、API 认证与既有安全约束；提供 Windows 一键启动/停止脚本；完成 pytest、tsc/vite 构建与真实浏览器验收。

## 2. 目录结构

```text
docs/TASK_EVIDENCE/TASK-002.3/
├── README.md                         # 本文件，证据索引
├── execution-report.md               # 执行过程与逐项验收结果
├── environment-report.md             # 实测环境版本与依赖
├── architecture-change-report.md     # 架构调整说明（Web 方向 vs 已取消的 Tauri）
├── known-issues.md                   # 已解决、未解决与后续风险
├── test-results/
│   ├── pytest-results.txt            # pytest 原始输出（20 passed）
│   ├── pytest-exit.txt               # pytest 退出码
│   ├── frontend-build.txt            # tsc -b && vite build 原始输出
│   └── frontend-build-exit.txt      # 前端构建退出码
├── screenshots/                      # 真实 Edge 浏览器验收截图（5 张）
├── logs/
│   ├── process-lifecycle.txt         # 进程树与 8000 端口监听记录
│   ├── web-static-check.txt           # 静态托管/SPA 回退检查记录
│   ├── web-api-smoke.txt             # 同源 API 冒烟记录（bootstrap/health/settings/services）
│   ├── environment-data-check.txt   # 数据目录、SQLite 版本与表结构核对
│   └── environment-versions.txt       # OS/Python/Node/关键依赖版本
└── git-diff/                        # 本次变更 diff 归档（提交前生成）
```

## 3. 结论概览

- pytest：20 passed（Python 3.13.18 / pytest 8.4.2，1 条 StarletteDeprecationWarning，非失败）。
- 前端：`tsc -b` 通过；`vite build` 成功，32 模块。
- 真实浏览器：Edge 访问 `127.0.0.1:8000` 正常连接并渲染设置页；刷新后 SPA 回退与会话保持正常。
- 生命周期：重复启动去重、停止释放端口与 PID、停止后再启动成功；仅监听 `127.0.0.1:8000`。
- 未完成与限制见 `known-issues.md`。
