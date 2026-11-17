# TASK-002.3.1 证据目录 — 本机 Web 安全加固与项目内数据目录迁移

- 任务编号：TASK-002.3.1
- 记录日期：2026-11-17
- 开发分支：`dev`（不合并 main）
- 版本：`0.1.0-dev.4`
- 执行人：豆包

## 1. 任务边界

在 TASK-002.3 本机 Web 架构基础上：

1. 将工作台默认数据根从 `%LOCALAPPDATA%\ComfyUI-Prompt-Workbench` 迁移到项目内 `userdata/`；旧目录保留不删，迁移前备份并做 SQLite 完整性校验。
2. 修复代码审查发现的问题：启动器监听绕过、PID 复用误杀、静态路径前缀碰撞、健康检查不验身份。
3. 补充自动化测试；更新控制文档；归档本证据目录；提交并推送 `origin/dev`，不合并 main。

## 2. 目录结构

```text
docs/TASK_EVIDENCE/TASK-002.3.1/
├── README.md                         # 本文件，证据索引
├── execution-report.md               # 执行过程与逐项验收结果
├── architecture-change-report.md      # 数据目录与安全加固的架构调整说明
├── data-directory-report.md           # 新旧目录对比、迁移结果与完整性核对
├── migration-report.md                 # 迁移动作、备份与旧数据保留情况
├── security-review-report.md          # 监听/PID 身份/进程树/静态路径/健康检查审查
├── environment-report.md              # 实测环境版本与依赖
├── known-issues.md                    # 已解决、未解决与后续风险
├── test-results/
│   ├── pytest-results.txt              # pytest 原始输出（36 passed）
│   ├── pytest-exit.txt                 # pytest 退出码
│   ├── frontend-build.txt             # tsc -b && vite build 原始输出
│   └── frontend-build-exit.txt        # 前端构建退出码
├── screenshots/                       # 真实 Edge 浏览器验收截图（3 张）
├── logs/
│   ├── environment-versions.txt       # OS/Python/Node/关键依赖版本
│   ├── data-directory-tree.txt        # 新旧目录树、文件大小与完整性
│   ├── gitignore-check.txt            # userdata 被 .gitignore 忽略的核对
│   ├── migration-report.txt           # 迁移后设置与备份目录记录
│   └── web-api-smoke.txt              # 健康身份探测/bootstrap/受保护端点/端口记录
└── git-diff/
    └── changes.diff                   # 本次变更 diff 归档（提交前生成）
```

## 3. 结论概览

- pytest：36 passed（Python 3.13.18 / pytest 8.4.2，1 条 StarletteDeprecationWarning，非失败）。
- 前端：`tsc -b` 通过；`vite build` 成功，32 模块。
- 数据迁移：旧库完整性 ok，迁入项目 `userdata/`，迁移前在 `userdata/backups/legacy-migration-<时间戳>/` 备份；旧目录原样保留；`userdata/` 被 Git 忽略，不入库。
- 安全加固：启动前校验 loopback；停止器按可执行路径 + 命令行 + 启动时间核验身份，fail-closed；静态路径用真实路径包含判断；健康检查为未认证身份探测并携带应用标识。
- 真机验收：Edge 访问 `127.0.0.1:8000`，服务已连接（Python 3.13.18），存储根目录显示为项目内 `userdata`；仅监听 `127.0.0.1:8000`。
- 未完成与限制见 `known-issues.md`。
