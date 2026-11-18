# Git 差异说明 — TASK-003.1-R4

## 变更文件

| 文件 | 改动 |
| --- | --- |
| `backend/workflow_service.py` | 新增 UI 节点控件名对齐与只读标量提取；模型 / LoRA 节点 `inputs` 不再为空 |
| `backend/test_workflow_service.py` | 新增 1 例 UI 加载器 / LoRA 控件值提取回归测试 |

## 统计

- 2 个文件改动，122 行新增，2 行删除（`git diff --stat`）。
- 原始 diff 见 `git-diff-raw.txt`。

## 未纳入版本控制

- `userdata/`（数据库、导入工作流副本、设置、日志等运行时数据）按 `.gitignore` 不入库。
- `.venv/`、`node_modules/`、`frontend/dist/`、PID / 运行记录文件不入库。
- 两份样本原始 JSON 作为证据复制到 `samples/` 一并入库；临时脚本与启动日志留在会话临时目录，不入库。
