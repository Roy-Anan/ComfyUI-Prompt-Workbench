# TASK-003.1-R2 证据目录

任务：按 ChatGPT 提供的完整 `backend/workflow_service.py` 修正版修复工作流解析与 Prompt 白名单写入；豆包负责落盘、测试、真机验证、证据归档与 Git 操作。

## 目录内容

| 文件 | 内容 |
| --- | --- |
| `Doubao-Receipt.md` | 豆包完整原始回执 |
| `execution-report.md` | 执行过程、实际修改文件、真机验收逐步结果 |
| `environment-report.md` | 运行环境、依赖、进程边界 |
| `test-results.md` | 后端 pytest 与前端构建结果、覆盖口径说明 |
| `pytest-output.txt` | pytest 原始命令输出 |
| `frontend-build.txt` | 前端 `npm run build` 原始输出 |
| `git-diff.md` / `git-diff-raw.txt` | 工作区差异说明与完整原始 diff |
| `known-issues.md` | 未闭环项、待补测试、遗留 warning |
| `screenshots/` | 真机页面截图 |
| `logs/` | 后端 uvicorn 访问日志 |

## 验收状态

- 后端 pytest：57 passed（exit 0）。
- 前端构建：通过（exit 0，33 模块）。
- 真机：页面可打开、服务已连接、工作流列表接口 200；**导入/写入闭环因缺少真实样本未完成**，详见 `known-issues.md`。
- 本目录不代表工作流功能已最终验收通过。
