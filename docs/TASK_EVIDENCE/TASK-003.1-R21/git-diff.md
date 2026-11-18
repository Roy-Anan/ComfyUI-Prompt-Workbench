# R21 Git Diff 摘要

基线：`55bff33`（R20 回执提交）。

## 改动文件

| 文件 | 改动 |
| --- | --- |
| `backend/value_normalize.py` | 尾部括号备注剥离；单值列表；raw 保留原值，+24/-3 |
| `backend/test_value_normalize.py` | 备注剥离、单值列表、两套建议不混并断言，+23 |
| `backend/test_rule_compare.py` | 剥离备注后调度器命中比对断言，+10 |
| `PROJECT_STATE.md` | 新增第 31 节 R21 记录 |
| `docs/ROADMAP.md` | 回填 R21 与后续切片口径 |
| `docs/TASK_EVIDENCE/TASK-003.1-R21/` | 本套证据 |

## 统计

```
PROJECT_STATE.md                | 26 ++++++++++++++++++++++++++
backend/test_rule_compare.py    | 10 ++++++++++
backend/test_value_normalize.py | 23 +++++++++++++++++++++++
backend/value_normalize.py      | 24 +++++++++++++++++++++---
docs/ROADMAP.md                 |  3 +++
5 files changed, 83 insertions(+), 3 deletions(-)
```

后端原始 diff 见 `git-diff-raw.txt`；证据目录在功能提交中一并入库。main 分支未改动。
