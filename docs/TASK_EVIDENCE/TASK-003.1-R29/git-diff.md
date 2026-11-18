# R29 Git Diff 摘要

基线：`b3b07f1`（R28 回执提交）。

## 改动文件

| 文件 | 改动 |
| --- | --- |
| `backend/workflow_service.py` | API/UI 两段新增 `latent_nodes`、`clip_skip_nodes` 全量收集与返回字段 |
| `backend/workflow_api.py` | actuals 透传 latent/CLIP 节点计数与摘要 |
| `backend/test_workflow_service.py` | 双 latent、双 CLIPSetLastLayer 解析断言 |
| `frontend/src/WorkflowWorkbench.tsx` | 多节点保守提示 |
| `PROJECT_STATE.md` | 第 39 节 R29 记录 |
| `docs/ROADMAP.md` | 回填 R29 |
| `docs/TASK_EVIDENCE/TASK-003.1-R29/` | 本套证据（截图与载荷样本） |

## 统计

```
PROJECT_STATE.md                   | 25 +++++++++++++++++++++++++
backend/test_workflow_service.py   | 29 +++++++++++++++++++++++++++++
backend/workflow_api.py            | 24 ++++++++++++++++++++++++
backend/workflow_service.py        | 36 ++++++++++++++++++++++++++++--------
docs/ROADMAP.md                    |  4 ++++
frontend/src/WorkflowWorkbench.tsx | 12 ++++++++++++
6 files changed, 122 insertions(+), 8 deletions(-)
```

原始 diff 见 `git-diff-raw.txt`。main 分支未改动。
