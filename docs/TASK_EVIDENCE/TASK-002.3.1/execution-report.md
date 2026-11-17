# 执行报告 — TASK-002.3.1

- 日期：2026-11-17
- 分支：`dev`
- 版本：`0.1.0-dev.4`

## 1. 基线核对

- 本地克隆：`D:\AI\ComfyUI-Prompt-Workbench-Git`，分支 `dev`。
- 起始提交：`039077b554d32f3096d141f3bf9d04a4f4eec98d`，工作区干净，与 `origin/dev` 同步。
- `main` 提交：`3084866aa85595133c7a1179b15ddd71e659d8f3`，本次未触碰。
- 既有 8 份基线文档与 `legacy-materials/` 目录保留，未覆盖、未删除。

## 2. 落地改动

### 2.1 数据目录服务（新增 `backend/datadir.py`）

- 默认数据根：环境变量 `WORKBENCH_DATA_ROOT` 优先；否则取仓库内 `userdata/`。
- 旧根识别：`%LOCALAPPDATA%\ComfyUI-Prompt-Workbench`（仅用于迁移判断，不再作为默认根）。
- 规划子目录：`database/ knowledge/ prompts/ workflows/ drafts/ history/ cache/ logs/ backups/ exports/`；设置文件落在 `settings/settings.json`。
- 迁移策略：
  - 旧根不存在 → 直接初始化新根。
  - 旧根无数据 → 不迁移。
  - 新根已有数据 → 不覆盖，记录 `skipped-conflict`。
  - 新根为空且旧根有数据 → 先在新根 `backups/legacy-migration-<时间戳>/` 备份，再复制非空文件；SQLite 文件跑 `PRAGMA integrity_check`，失败保留旧数据。
  - 旧目录永不删除；旧根根级 `settings.json` 不复制（管理路径按新根重建，外部 checkpoint/lora 路径保留）。

### 2.2 后端重构（`backend/main.py`）

- 接入 `datadir`：`DATA_ROOT`、`SETTINGS_FILE` 由统一路径服务提供；版本号升至 `0.1.0-dev.4`；`MIGRATION_REPORT` 记录本次迁移结果。
- 静态托管 `_resolve_within_dist()`：先 `urllib.parse.unquote` 解码 URL 编码，再 `Path.resolve()` 后用 `relative_to(dist_root)` 做真实路径包含判断，拒绝 `../`、`%2e%2e%2f` 与相邻目录前缀碰撞（如 `dist-other`）。
- 新增 `is_loopback_host()`：接受 `127.0.0.1` / `localhost` / `::1` 及解析后全为回环的名字；拒绝 `0.0.0.0`、局域网与公网 IP。
- `/api/health` 响应体增加 `app` / `app_id` 应用标识；中间件对 `/api/health` 提前放行作为未认证身份探测（仅暴露应用标识与版本，不含用户数据），其余受保护端点仍需会话。

### 2.3 启动器加固（`scripts/workbench_launcher.py`）

- 启动前校验监听地址为 loopback，非法地址直接退出。
- `health_identifies_workbench()` 解析 `/api/health` JSON，要求 `app` 或 `app_id` 等于 `ComfyUI-Prompt-Workbench` 才判定就绪，不再凭任意 HTTP 响应判定。
- 重复启动 / 端口占用时先验身份：非本工作台实例不结束，只提示。

### 2.4 停止器加固（`scripts/workbench_stopper.py`）

- 不再仅凭 PID：经 CIM 读取 `ExecutablePath` / `CommandLine` / `CreationDate`，校验可执行路径为项目 `.venv\Scripts\python.exe`、命令行含 `uvicorn` 与 `main:app` 且指向项目后端。
- 任一关键属性缺失或不匹配即 fail-closed，不终止、输出警告保留现场。
- 递归收集整棵进程树；禁止按 Python / uvicorn 名称批量结束。

### 2.5 忽略规则（`.gitignore`）

- 新增 `/userdata/`、`*.tmp`；保留 `.workbench.pid`、`*.log`、`.venv/`、`node_modules/`、`frontend/dist/` 与 legacy 归档路径。

## 3. 逐项验收结果

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| pytest 后端 + 脚本 | 通过 | 36 passed，5.55s（Python 3.13.18 / pytest 8.4.2，1 条弃用警告） |
| TypeScript 类型检查 | 通过 | `tsc -b` 退出码 0 |
| Vite 生产构建 | 通过 | 32 模块，JS 148.16 kB / CSS 2.77 kB / HTML 0.41 kB，613ms |
| 新根目录初始化 | 通过 | 10 个管理子目录 + `settings/` 建立 |
| 旧库完整性 | 通过 | `PRAGMA integrity_check` = ok，`schema_version=1`，`app_metadata` 正常 |
| 迁移备份 | 通过 | `backups/legacy-migration-20261117-145437/` 保留旧库副本 |
| 新库完整性 | 通过 | 迁入后 `integrity_check` = ok，版本 1，元数据正常 |
| 旧目录保留 | 通过 | 旧根两文件原样存在，未删除 |
| `userdata` 被忽略 | 通过 | `git check-ignore` 命中 `.gitignore:28 /userdata/` |
| 监听地址限制 | 通过 | 仅 `127.0.0.1:8000` 监听；loopback 校验拒绝非回环地址 |
| PID 身份核验 | 通过 | 停止器正确识别并回收工作台进程树；身份不匹配 fail-closed |
| 静态路径穿越拒绝 | 通过 | `../`、编码穿越、相邻前缀碰撞解析结果均为 None |
| 健康身份探测 | 通过 | 无会话 200 且携带应用标识；受保护端点仍 401 |
| 浏览器真机验收 | 通过 | Edge 连接成功，存储根显示项目内 `userdata` |

## 4. 未做事项（边界外）

- 未实现 Prompt 编辑器、知识库、角色管理、工作流解析、规则引擎、队列、显存调度、出图闭环等业务功能。
- 未安装 Rust/MSVC/系统工具；未启动、关闭或重启 ComfyUI / Ollama。
- 未推送或合并 `main`；本次仅在 `dev` 提交。
