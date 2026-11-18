# R22 Git Diff 摘要

基线：`a189121`（R21 回执提交）。

## 改动文件

| 文件 | 改动 |
| --- | --- |
| `backend/workflow_service.py` | latent 节点识别与宽高提取，API/UI 两段写入报告 `latent`，+29 |
| `backend/workflow_api.py` | `_sampler_actuals` 合并 latent 宽高到比对 actuals，+14/-3 |
| `backend/rule_compare.py` | Resolution 宽高集合专用比对，+53/-3 |
| `backend/test_workflow_service.py` | latent 提取 / 缺失断言，+15 |
| `backend/test_workflow_rules.py` | compare actuals 宽高断言，+3 |
| `backend/test_rule_compare.py` | Resolution match / out_of_set / 缺尺寸 unknown 断言，+29 |
| `PROJECT_STATE.md` | 新增第 32 节 R22 记录 |
| `docs/ROADMAP.md` | 回填 R22 与后续切片口径 |
| `docs/TASK_EVIDENCE/TASK-003.1-R22/` | 本套证据 |

## 统计

```
PROJECT_STATE.md                 | 25 +++++++++++++++++++
backend/rule_compare.py          | 53 +++++++++++++++++++++++++++++++++++++---
backend/test_rule_compare.py     | 29 ++++++++++++++++++++++
backend/test_workflow_rules.py   |  3 +++
backend/test_workflow_service.py | 15 ++++++++++++
backend/workflow_api.py          | 14 ++++++++---
backend/workflow_service.py      | 29 ++++++++++++++++++++++
docs/ROADMAP.md                  |  3 +++
8 files changed, 165 insertions(+), 6 deletions(-)
```

后端原始 diff 见 `git-diff-raw.txt`；证据目录在功能提交中一并入库。main 分支未改动。
