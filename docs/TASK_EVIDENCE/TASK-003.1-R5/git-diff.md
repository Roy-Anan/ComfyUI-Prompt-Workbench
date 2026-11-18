# Git 差异说明 — TASK-003.1-R5

## 变更文件

| 文件 | 改动 |
| --- | --- |
| `backend/test_workflow_service.py` | 新增 1 条真实导出 API 工作流的全链路写回回归用例（111 行新增） |

## 统计

- 1 个文件改动，111 行新增，0 行删除（`git diff --stat`，相对 R4 提交 `52d8d3a`）。
- 服务端解析/写入逻辑、前端代码本轮无改动。
- 原始 diff 见 `git-diff-raw.txt`。

## 未纳入版本控制

- `userdata/`（数据库、导入工作流副本、设置、日志、版本快照）按 `.gitignore` 不入库；本轮真机导入的工作流副本只留在本机运行时数据目录。
- `.venv/`、`node_modules/`、`frontend/dist/`、PID / 运行记录文件不入库。
- 临时验证脚本与启动日志留在会话临时目录，不入库。
