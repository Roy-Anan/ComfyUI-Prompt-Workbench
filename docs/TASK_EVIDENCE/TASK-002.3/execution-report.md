# 执行报告 — TASK-002.3

- 日期：2026-11-17
- 分支：`dev`
- 版本：`0.1.0-dev.3`

## 1. 执行内容

1. 盘点现有代码耦合：前端唯一 Tauri 耦合为 `@tauri-apps/api/core` 的 `invoke`（取后端端口/令牌）；后端原为 Bearer 头认证、无静态托管。
2. 后端改造为 Web 模式：静态托管 `frontend/dist/`、SPA 回退、`/api/*` JSON 404、缺失 dist 503、路径越界 403；新增 `/api/bootstrap` 会话票据与 CSRF；Origin 白名单；loopback 绑定校验。
3. 前端去除 Tauri：新增同源 `api.ts`；`App.tsx` 改用 `apiGet/apiPost`；`package.json` 移除 Tauri 运行依赖、CLI 与 `tauri` script。
4. Tauri 残留归档：`frontend/src-tauri/` 整体移入 `legacy/src-tauri/`，内容保留未删；新增 `legacy/README.md`。
5. 依赖拆分：pytest 移入 `backend/requirements-dev.txt`；运行清单 `requirements.txt` 不再含测试依赖。
6. 一键启停：`scripts/workbench_launcher.py`、`scripts/workbench_stopper.py`、根目录 `启动工作台.bat`、`停止工作台.bat`。

## 2. 逐项验收结果

| # | 验收项 | 结果 | 证据 |
| --- | --- | --- | --- |
| 1 | Python pytest | 通过：20 passed，5.26s，1 条弃用警告 | `test-results/pytest-results.txt`、`pytest-exit.txt`（退出码 0） |
| 2 | TypeScript 类型检查 | 通过：`tsc -b` 退出码 0 | `test-results/frontend-build.txt` |
| 3 | Vite 生产构建 | 通过：32 模块，JS 148.16 kB / CSS 2.77 kB / HTML 0.41 kB，673ms | `test-results/frontend-build.txt`、`frontend-build-exit.txt` |
| 4 | SQLite 创建与版本保留 | 通过：`workbench.sqlite3` 两表，schema_version=1，重复初始化保留版本 | `logs/environment-data-check.txt` |
| 5 | API 认证（成功/失败） | 通过：无会话 401；票据/Bearer 授权 200；外部 Origin 状态变更 403 | `logs/web-api-smoke.txt`、`test-results/pytest-results.txt` |
| 6 | CSRF 防护 | 通过：Cookie 会话缺 CSRF 头 403；带头 200 | pytest 用例 `test_post_requires_csrf_header` |
| 7 | 浏览器真实访问 | 通过：Edge 访问 `http://127.0.0.1:8000`，服务卡片显示已连接 Python 3.13.18 | `screenshots/browser-1-connected.png`、`browser-2-settings.png`、`browser-3-storage.png` |
| 8 | SPA 刷新回退与会话保持 | 通过：刷新后重新 bootstrap，设置/存储数据回填 | `screenshots/browser-4-after-refresh.png`、`browser-5-refresh-restored.png` |
| 9 | 端口绑定 | 通过：仅监听 `127.0.0.1:8000`，未绑 `0.0.0.0` | `logs/process-lifecycle.txt` |
| 10 | 重复启动去重 | 通过：第二次启动识别已有实例（PID 18864），不产生第二个进程 | 现场命令输出，见下 |
| 11 | 停止生命周期 | 通过：按 PID 终止进程树；端口监听计数 0；PID 文件清除 | 现场命令输出；停止脚本退出码 0 |
| 12 | 停止后再启动 | 通过：再次启动 PID 31640，根路径 200，监听 127.0.0.1:8000 | 现场命令输出 |
| 13 | Ollama 离线兼容 | 通过：离线 `online:false`，WinError 10061，服务 200 不崩溃 | `logs/web-api-smoke.txt` |
| 14 | ComfyUI 离线兼容 | 通过：离线 `online:false`，WinError 10061，服务 200 不崩溃 | `logs/web-api-smoke.txt` |
| 15 | 用户数据保护 | 通过：数据根在 `%LOCALAPPDATA%\ComfyUI-Prompt-Workbench`，未进构建目录；未删除/重建数据库 | `logs/environment-data-check.txt` |

## 3. 现场命令关键记录

- 重复启动：`[工作台] 已有实例在运行（PID 18864，端口 8000）。`，第二次启动退出码 0，未新增监听进程。
- 停止：`[工作台] 已停止工作台进程 18864（含其子进程），未影响其他服务。`，停止后 `Get-NetTCPConnection -LocalPort 8000` 监听计数为 0，`.workbench.pid` 不存在。
- 再启动：`[工作台] 服务已就绪（PID 31640）。`，根路径 `GET /` 返回 200。

## 4. 未执行 / 未完成

- 真实出图端到端验收：不在本次边界内。
- Ollama / ComfyUI 在线状态下的真实调用：本次仅离线连通性检测。
- Python 3.12 兼容性：本机仅 3.13.18，未单独验证 3.12。
