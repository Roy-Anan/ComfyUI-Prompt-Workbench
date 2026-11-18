# R18 Git Diff 摘要

基线：`2b5c14f`（R17 回执提交）。

## 改动文件

| 文件 | 改动 |
| --- | --- |
| `backend/rule_prompt.py` | 新增：`build_prompt_context()` 提示载荷装配层 |
| `backend/rule_engine.py` | `resolve_field`/`resolve_context` 增加可选 `architecture_scope`，+14/-2 |
| `backend/workflow_api.py` | 新增 `GET /api/workflows/{id}/rules/prompt`，+36 |
| `backend/test_rule_prompt.py` | 新增 3 例纯函数测试 |
| `backend/test_workflow_rules.py` | 补 2 例接口层提示载荷断言 |
| `PROJECT_STATE.md` | 新增第 28 节 R18 记录 |
| `docs/ROADMAP.md` | 回填 R18 与后续切片口径 |
| `docs/TASK_EVIDENCE/TASK-003.1-R18/` | 本套证据 |

## 统计

```
PROJECT_STATE.md               | 26 ++++++++++++++++++++++++++
backend/rule_engine.py         | 14 ++++++++++++--
backend/test_workflow_rules.py | 42 ++++++++++++++++++++++++++++++++++++++++++
backend/workflow_api.py        | 36 ++++++++++++++++++++++++++++++++++++
docs/ROADMAP.md                |  5 ++++-
5 files changed, 120 insertions(+), 3 deletions(-)
```

后端原始 diff 见 `git-diff-raw.txt`；未跟踪新文件（`rule_prompt.py`、`test_rule_prompt.py`、证据目录）在功能提交中一并入库。main 分支未改动。
