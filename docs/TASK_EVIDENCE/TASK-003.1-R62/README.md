# TASK-003.1-R62 R60/R61 阶段真机验收；R63 首载并发 500 修复

## 验收范围

- R60：生成历史「列表 / 网格 / 时间轴」三视图切换，时间轴按提交日期分组；视图偏好沿用本地记忆。
- R61：启停脚本 PowerShell 路径解析与进程身份校验修复（详见 R61 证据目录）。
- 基线：health `0.1.0-dev.5` / Python 3.13.18；Ollama `127.0.0.1:11434` 在线、ComfyUI `127.0.0.1:8188` 在线；
  diagnostics counts `rules=0, history=0, tasks=0, model_identities=16, workflows=22, profiles=13`，`database_error=None`。

## 首载并发 500 现象（R62 走查定位）

- 浏览器首载 `Promise.all` 并发打六个端点（health / settings / services/status / models/catalog / rules / profiles），
  任一 reject 即整体 catch，health 保持 null，界面显示「未连接 500」；刷新后偶发恢复。
- 串行逐端点直连全部 200；线程池并发复现偶发 500：`/api/services/status`、`/api/rules`、`/api/settings`。
- 带日志复现拿到 traceback：`services_status` / `list_rules` → `load_settings()` →
  `datadir.prepare_root()` → `migrate_legacy_settings()` → `save_settings_file()` →
  `tmp.replace(settings.json)` → `PermissionError: [WinError 5] 拒绝访问`。

## 根因（R63）

- `load_settings()` 每次调用都跑 `prepare_root()`；只要 legacy AppData `settings.json` 仍在
  （迁移后旧文件按设计保留），`migrate_legacy_settings()` 就重新 merge 并 `save_settings_file` 重写
  userdata `settings.json`。
- 首载并发下多个工作线程同时 `os.replace` 同一 `settings.json`，Windows 文件锁冲突抛 WinError 5 → 500。
  非 SQLite 锁、非旧 JS 缓存。

## 修复（R63，`backend/main.py`）

- 数据根准备（建目录 + 一次性 legacy 迁移）改为**进程内一次性执行**：新增 `_root_prepared` 标志与
  `threading.Lock`；`load_settings()` 在锁内双检，仅首个调用执行 `prepare_root()` 并置标志，后续请求
  跳过迁移直接读设置。`MIGRATION_REPORT` 保留首次结果。
- 新增并发回归测试 `test_concurrent_settings_load_does_not_race_legacy_rewrite`：legacy 设置存在时，
  8 线程 ×16 次并发 `load_settings()` 全部成功、设置可读、`_root_prepared` 为真。

## 真机闭环（本机 127.0.0.1:17890）

- 修复前：并发 6 线程 ×3 轮复现 settings / rules / services/status 500。
- 修复后：并发 6 线程 ×3 轮六端点全 200；加重为 10 线程 ×6 轮 ×18 请求，无 500 / 无错误。
- 浏览器真机：设置页首载即「已连接 Python 3.13.18，Ollama 在线，ComfyUI 在线」；历史页首载干净空态，
  三视图按钮在位（空态禁用）、导出 JSON 禁用、刷新可用、「暂无生成历史」；工作流工作区页正常。
- 收尾：stopper 按结构化身份回收实例（PID 15528，含子进程），端口关闭，`.workbench.pid` /
  `.workbench-runtime.json` 记录清理；Ollama、ComfyUI 外部进程未触碰。

## 回归

- 后端：**225 passed, 1 warning**（`pytest-output.txt`；224 基线 + 新增并发回归 1；
  StarletteDeprecationWarning 为遗留，与本项目无关）。
- 前端：本切片无前端改动，构建绿；产物哈希沿用 R60
  （`index-DfaJ9V43.js` 177.97 kB / gzip 56.60 kB，`index-Ol_zgAo6.css` 9.11 kB / gzip 2.28 kB），
  见 `frontend-build.txt`。

## 边界与遗留

- 历史库为空，时间轴分组的真机分组渲染留待有生成记录的阶段收口走查；本次仅验证三视图按钮与空态禁用态。
- 本次只修设置迁移路径的并发写；SQLite 与其他文件的并发读写锁仍属既有 backlog，未扩范围。
- 未改动白名单写入、CSRF、回环绑定、fail-closed 等安全口径。
