# TASK-002.3.2 证据：进程身份校验加固与旧设置无损迁移

## 任务范围
基于 dev 分支，只解决两件事：
1. 停止工作台时用结构化运行记录真正比对进程身份，PID 复用或任一不匹配即拒绝终止。
2. 将旧版 AppData `settings.json` 无损迁移/安全合并到项目内 `userdata/settings/settings.json`。

不重迁数据库，不改 main，不扩大范围。

## 结论
- 后端 pytest：48 passed，退出码 0（见 `test-results/pytest-results.txt`）。
- 真机启停：启动就绪（PID 7908）→ 健康检查实例标识与记录一致 → 身份核验通过 → 正常停止，进程树回收，8000 端口释放，运行记录清理（见 `logs/runtime-lifecycle.txt`）。
- 旧设置迁移：连接地址、Checkpoint、LoRA 路径保留；管理路径按新 userdata 重建；新设置已存在时安全合并不覆盖；旧文件保留（见 `logs/settings-migration.txt`）。
- 代码改动：见 `git-diff/changes.diff`。

## 进程身份校验要点
- 启动器写入结构化记录：PID、进程启动时间（ISO8601）、可执行路径、工作目录、命令行、随机实例标识、host/port。
- 停止器读取记录并逐项比对：app_id、实例标识（经本机健康检查回传）、PID、可执行路径、工作目录、命令行、CreationDate。
- 记录缺失/损坏、身份无法确认、任一不匹配：fail-closed，不杀进程，给出明确错误。
- 正常停止后清理结构化记录与旧 PID 文件。
- 仅回收本工作台进程树；不按名称批量杀 Python，不触碰 Ollama/ComfyUI/其他 Python。

## 目录
- `test-results/`：pytest 原始输出与退出码记录。
- `logs/`：真机生命周期记录、设置迁移前后对照。
- `git-diff/`：本次实际修改内容。
- `known-issues.md`：尚未解决但影响后续开发的问题。
