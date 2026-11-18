# R23 Git Diff 摘要

基线：`b98b74c`（R22 回执提交）。

## 改动文件

| 文件 | 改动 |
| --- | --- |
| `backend/value_normalize.py` | Resolution 基于原始文本提取括号内尺寸并去重；数值/列表维持备注剥离，+26/-6 |
| `backend/test_value_normalize.py` | 括号内尺寸提取、重复去重断言，+20 |
| `PROJECT_STATE.md` | 新增第 33 节 R23 记录 |
| `docs/ROADMAP.md` | 回填 R23 与后续切片口径 |
| `docs/TASK_EVIDENCE/TASK-003.1-R23/` | 本套证据 |

## 统计

```
PROJECT_STATE.md                | 25 +++++++++++++++++++++++++
backend/test_value_normalize.py | 20 ++++++++++++++++++++
backend/value_normalize.py      | 26 ++++++++++++++++++++------
docs/ROADMAP.md                  |  3 +++
4 files changed, 68 insertions(+), 6 deletions(-)
```

后端原始 diff 见 `git-diff-raw.txt`；证据目录在功能提交中一并入库。main 分支未改动。
