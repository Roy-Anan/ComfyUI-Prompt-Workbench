# R19 Git Diff 摘要

基线：`c7d75a2`（R18 回执提交）。

## 改动文件

| 文件 | 改动 |
| --- | --- |
| `backend/rule_compare.py` | 新增：保守比对纯函数层 |
| `backend/workflow_service.py` | 采样器组补 `params` 快照与 `_sampler_params()`，+18 |
| `backend/rule_prompt.py` | 字段条目携带 `structured`，+12/-2 |
| `backend/workflow_api.py` | 新增 `GET /api/workflows/{id}/rules/compare` 与 `_sampler_actuals()`，+46 |
| `backend/test_rule_compare.py` | 新增 8 例纯函数比对测试 |
| `backend/test_workflow_rules.py` | 补 2 例接口层比对断言 |
| `PROJECT_STATE.md` | 新增第 29 节 R19 记录 |
| `docs/ROADMAP.md` | 回填 R19 与后续切片口径 |
| `docs/TASK_EVIDENCE/TASK-003.1-R19/` | 本套证据 |

## 统计

```
PROJECT_STATE.md               | 26 ++++++++++++++++++++++++
backend/rule_prompt.py         | 12 +++++++++--
backend/test_workflow_rules.py | 45 +++++++++++++++++++++++++++++++++++++++++
backend/workflow_api.py        | 46 ++++++++++++++++++++++++++++++++++++++++++
backend/workflow_service.py    | 18 +++++++++++++++++
docs/ROADMAP.md                |  3 +++
6 files changed, 148 insertions(+), 2 deletions(-)
```

后端原始 diff 见 `git-diff-raw.txt`；未跟踪新文件（`rule_compare.py`、`test_rule_compare.py`、证据目录）在功能提交中一并入库。main 分支未改动。
