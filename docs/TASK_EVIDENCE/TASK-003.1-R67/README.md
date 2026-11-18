# TASK-003.1-R67 M9 整库备份只读导出（ZIP + 清单）

## 验收范围

- M9 验收口径「备份覆盖所有约定数据域」的只读切片：把当前工作台持久用户数据打包为本地
  ZIP 并附清单 `manifest.json`，供本地留存 / 迁移。本切片**只导出不恢复**；
  带完整性校验的恢复写入属高风险操作，留后续切片。
- 基线：health `0.1.0-dev.5` / Python 3.13.18；`rules=0`，`profiles=13`，`workflows=22`；
  Ollama `127.0.0.1:11434`、ComfyUI `127.0.0.1:8188` 在线。

## 纳入 / 排除口径（保守）

- **纳入**：`settings/settings.json`（仅当前设置文件）、`database/workbench.sqlite3`、
  `workflows/`（工作流副本 + 历史版本快照）、`knowledge/`、`prompts/`、`drafts/`、`history/`。
- **排除**：`cache/`（可重建缓存）、`logs/`（运行日志）、`backups/`（历史备份自身）、
  `exports/`（既有导出物）；`settings.corrupt-*.json` 损坏设置旁车文件不纳入。
- **外部目录**：checkpoint / LoRA / CLIP / VAE / output 只在清单登记配置路径与是否存在，
  **不拷贝模型权重、LoRA/CLIP/VAE 文件或 ComfyUI 原图**。

## 后端实现要点（`backend/backup_export.py` / `main.py`）

- `build_backup_archive(root, version)`：收集纳入域文件，逐文件字节入 ZIP；单个不可读文件
  跳过并在清单保守记录，不中断整包。路径经 `resolve().relative_to(root)` 防越界。
- 数据库用 SQLite **backup API** 在线备份到临时文件（不直接拷贝正在使用的库文件），
  归档成员为可直接打开的真实 `.sqlite3`（非 SQL dump）；`PRAGMA integrity_check` 结果记入清单。
- `manifest.json`：导出时间、app/version、data_root、各纳入域文件计数与字节数、
  数据库完整性与字节数、排除域清单、外部目录路径记录、连接地址、范围说明。
- 端点：`GET /api/backup/export`（GET 免 CSRF，走既有会话鉴权中间件）；
  `Content-Type: application/zip`，`Content-Disposition: attachment; filename=workbench-backup-*.zip`。
- 测试 `test_backup_export.py` 2 例：
  - 纳入域（设置 / 库 / 五个资料域）与清单在位；排除域与损坏旁车不进包；归档库可打开且
    `workbench_rule` 等表在；数据库 integrity 为 `ok`。
  - 外部 output 目录路径仅登记、`exists=True`；目录内原图不进包。

## 前端实现要点（`frontend/src/App.tsx` / `api.ts`）

- `api.ts` 新增 `apiGetBlob(path)`：同源 GET 取二进制 Blob（会话 cookie 自动携带，GET 无需 CSRF）。
- 设置页按钮「导出整库备份」：拉取 ZIP Blob，按时间戳命名 `workbench-backup-*.zip` 触发浏览器下载；
  成功消息「整库备份已导出（仅本地 ZIP；不含模型权重与原图）。」；失败回显错误；导出期间禁用。

## 真机闭环（本机 127.0.0.1:17890，PID 11800）

- 后端直连（会话 cookie）：`GET /api/backup/export` → 200，`application/zip`，
  `workbench-backup-20261118-102530.zip`，77,986 字节。
- 包内：`manifest.json`、`settings/settings.json`、`database/workbench.sqlite3`（69,632 字节，
  integrity `ok`）、`workflows/` 90 个文件（22 个工作流副本 + 2 条历史版本快照）；
  knowledge/prompts/drafts/history 计数 0（当前为空域，结构保留）。
- 归档库回写临时文件后 `PRAGMA integrity_check` 为 `ok`，表含 `workbench_rule`、
  `generation_history`、`comfy_task`、`model_identity`、`schema_version`、`app_metadata`。
- 排除域 `cache/logs/backups/exports/` 与损坏设置旁车均未出现在包内；外部目录当前未配置，
  清单记 `configured=""`、`exists=false`。
- 浏览器：服务与设置页「导出整库备份」按钮在位；点击后网络请求 `/api/backup/export` GET `ok`，
  无 console 报错；消息「整库备份已导出（仅本地 ZIP；不含模型权重与原图）。」。
- 截图：`r67-settings-buttons.png`（设置页导出按钮区）、`r67-backup-success.png`（导出成功消息）。

## 收尾

- 本切片为只读导出，未写入或删除任何用户数据；`rules=0`、`profiles=13`、`workflows=22` 保持基线。
- stopper 按结构化身份回收实例（PID 11800，含子进程），端口 17890 关闭；Ollama、ComfyUI 外部进程未触碰。

## 回归

- 后端：**231 passed, 1 warning**（`pytest-output.txt`；StarletteDeprecationWarning 为遗留，
  与本项目无关）。较 R66 基线 229 增加 2 例（备份打包 + 外部路径登记）。
- 前端：`tsc -b && vite build` 绿（`frontend-build.txt`）；产物
  `index-Cy3p6Q7D.js` 181.47 kB / gzip 57.84 kB，`index-X0JFovQF.css` 9.42 kB / gzip 2.33 kB。

## 边界与遗留

- 未实现：备份**恢复**写入、恢复前完整性校验与冲突合并（高风险，单独切片）；数据库迁移；
  崩溃恢复与数据完整性巡检（M9 既有 backlog）。
- 备份不含模型权重与原图；换机迁移需另行在目标机就位 ComfyUI 模型目录。
- 未改动白名单写入、CSRF、回环绑定、unknown 不臆测等安全口径。
