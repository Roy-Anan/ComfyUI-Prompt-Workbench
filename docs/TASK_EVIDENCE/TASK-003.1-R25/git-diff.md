# R25 Git Diff 摘要

基线：`c791625`（R24 回执提交）。

## 改动文件

| 文件 | 改动 |
| --- | --- |
| `backend/workflow_api.py` | 遍历全部采样器组，新增 `sampler_group_count` / `sampler_groups`；顶层取首组，+19/-3 |
| `backend/test_workflow_rules.py` | 双组样本断言，+24 |
| `PROJECT_STATE.md` | 第 35 节 R25 记录 |
| `docs/ROADMAP.md` | 回填 R25 |
| `docs/TASK_EVIDENCE/TASK-003.1-R25/` | 本套证据 |

## 统计

```
PROJECT_STATE.md               | 22 ++++++++++++++++++++++
backend/test_workflow_rules.py | 24 ++++++++++++++++++++++++
backend/workflow_api.py        | 19 ++++++++++++++++---
docs/ROADMAP.md                 |  3 +++
4 files changed, 65 insertions(+), 3 deletions(-)
```

后端原始 diff 见 `git-diff-raw.txt`。main 分支未改动。
