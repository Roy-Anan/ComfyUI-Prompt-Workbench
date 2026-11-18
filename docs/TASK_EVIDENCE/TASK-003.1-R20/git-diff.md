# R20 Git Diff 摘要

基线：`c5390c2`（R19 回执提交）。

## 改动文件

| 文件 | 改动 |
| --- | --- |
| `backend/architecture_normalize.py` | 新增：标签归一化纯函数层 |
| `backend/rule_store.py` | 家族归并上下文归集、身份指针解析、未登记不猜家族，+110/-35 |
| `backend/profile_parser.py` | 补 checkpoint 桶 `IDENTITY::Base Architecture` 身份指针 |
| `backend/rule_prompt.py` | 载荷透传 `architecture_family`/`architecture_label` |
| `backend/workflow_api.py` | 未登记占位补家族/标签字段 |
| `backend/test_architecture_normalize.py` | 新增 8 例归一化单测 |
| `backend/test_rule_store.py` | 同家族归并、混合隔离 2 例 |
| `backend/test_profile_source.py` | 身份指针落库断言同步 |
| `backend/test_workflow_rules.py` | 未登记不带家族断言 |
| `PROJECT_STATE.md` | 新增第 30 节 R20 记录 |
| `docs/ROADMAP.md` | 回填 R20 与后续切片口径 |
| `docs/TASK_EVIDENCE/TASK-003.1-R20/` | 本套证据 |

## 统计

```
PROJECT_STATE.md               |  28 +++++++++++
backend/profile_parser.py      |  20 ++++++++
backend/rule_prompt.py         |   6 +++
backend/rule_store.py          | 110 +++++++++++++++++++++++++++++------------
backend/test_profile_source.py |   9 +++-
backend/test_rule_store.py     |  48 ++++++++++++++++++
backend/test_workflow_rules.py |   2 +
backend/workflow_api.py        |   6 +++
docs/ROADMAP.md                |   5 +-
9 files changed, 199 insertions(+), 35 deletions(-)
```

后端原始 diff 见 `git-diff-raw.txt`；未跟踪新文件（`architecture_normalize.py`、`test_architecture_normalize.py`、证据目录）在功能提交中一并入库。main 分支未改动。
