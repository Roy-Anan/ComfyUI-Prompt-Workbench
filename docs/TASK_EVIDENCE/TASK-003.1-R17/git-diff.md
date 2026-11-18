# R17 Git Diff 摘要

基线：`d04f0cf`（R16 回执提交）。

## 改动文件

| 文件 | 改动 |
| --- | --- |
| `backend/rule_store.py` | 新增 `context_for_checkpoint()` 与架构标签关联（架构桶回退），+77 |
| `backend/workflow_api.py` | 新增 `GET /api/workflows/{id}/rules`、`_database_path()`、`_checkpoint_filename()`，+47 |
| `backend/test_workflow_rules.py` | 新增 3 例上下文规则接口测试 |
| `PROJECT_STATE.md` | 新增第 27 节 R17 记录 |
| `docs/ROADMAP.md` | 回填 R17 与后续切片口径 |
| `docs/TASK_EVIDENCE/TASK-003.1-R17/` | 本套证据 |

## 统计

```
PROJECT_STATE.md        | 26 +++++++++++++++++
backend/rule_store.py   | 77 +++++++++++++++++++++++++++++++++++++++++++++++++
backend/workflow_api.py | 47 ++++++++++++++++++++++++++++++
docs/ROADMAP.md         |  9 ++++--
4 files changed, 156 insertions(+), 3 deletions(-)
```

后端原始 diff 见 `git-diff-raw.txt`；未跟踪测试文件与证据目录在功能提交中一并入库。main 分支未改动。
