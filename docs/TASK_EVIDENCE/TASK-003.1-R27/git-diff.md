# R27 Git Diff 摘要

基线：`d6f825e`（R26 回执提交）。

## 改动文件

| 文件 | 改动 |
| --- | --- |
| `backend/rule_compare.py` | 抽出 `_count`；新增 `sampler_group_comparisons` 逐组独立比对 |
| `backend/test_workflow_rules.py` | 种子 Steps 规则补结构化；双组逐组结论与分组计数断言 |
| `frontend/src/WorkflowWorkbench.tsx` | `GroupComparison` 类型与逐组卡片渲染 |
| `frontend/src/styles.css` | 分组卡片样式 |
| `PROJECT_STATE.md` | 第 37 节 R27 记录 |
| `docs/ROADMAP.md` | 回填 R27 |
| `docs/TASK_EVIDENCE/TASK-003.1-R27/` | 本套证据（两张截图与载荷样本） |

## 统计

```
PROJECT_STATE.md                   | 22 ++++++++++++
backend/rule_compare.py            | 48 ++++++++++++++++++++++----
backend/test_workflow_rules.py     | 13 +++++++
docs/ROADMAP.md                    |  3 ++
frontend/src/WorkflowWorkbench.tsx | 71 ++++++++++++++++++++++++++++++++++++++
frontend/src/styles.css             | 21 +++++++++++
6 files changed, 171 insertions(+), 7 deletions(-)
```

原始 diff 见 `git-diff-raw.txt`。main 分支未改动。
