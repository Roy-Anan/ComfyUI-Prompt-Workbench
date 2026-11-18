# Git Diff 说明 — TASK-003.1-R8

## 改动概览

| 文件 | 类型 | 说明 |
| --- | --- | --- |
| `backend/model_identity.py` | 修改 | 新增摘要归并查询 `identity_group`；摘要回挂身份键/副本数/副本列表 |
| `backend/test_model_identity.py` | 修改 | 追加 3 例归并测试（同摘要归并、不同内容不合并、未哈希无身份键） |
| `frontend/src/App.tsx` | 修改 | 补充副本与身份键类型字段 |
| `docs/ROADMAP.md`、`PROJECT_STATE.md` | 修改 | 回填 R8 状态与路线图 |

## 统计

`git diff --stat`（已跟踪文件，提交前工作区）：

```
backend/model_identity.py      | 77 ++++++++++++++++++++++++++++++++++++++++--
backend/test_model_identity.py | 55 ++++++++++++++++++++++++++++++
frontend/src/App.tsx           |  9 +++++
3 files changed, 139 insertions(+), 2 deletions(-)
```

新增未跟踪文件：`docs/TASK_EVIDENCE/TASK-003.1-R8/`。

原始 diff 见 `git-diff-raw.txt`（仅含已跟踪文件的改动；新增证据文件以工作区文件为准）。

## 未改动

- `backend/main.py`、`backend/model_catalog.py`、`backend/workflow_service.py`、`backend/workflow_api.py`、`backend/datadir.py`、`frontend/src/styles.css` 本轮未改。
- main 分支未改动；所有改动落在 dev。
