# Git Diff 说明 — TASK-003.1-R7

## 改动概览

| 文件 | 类型 | 说明 |
| --- | --- | --- |
| `backend/model_identity.py` | 新增 | SQLite 身份表、目录索引、元数据刷新、按需流式 SHA256、身份摘要 |
| `backend/test_model_identity.py` | 新增 | 7 例身份库单元测试 |
| `backend/main.py` | 修改 | 初始化身份表 schema；清单接口索引目录并回挂 identity 摘要 |
| `backend/test_model_catalog.py` | 修改 | 追加 1 例接口身份回挂测试 |
| `frontend/src/App.tsx` | 修改 | 身份摘要类型、大小格式化、已校验/未哈希标签 |
| `docs/ROADMAP.md`、`PROJECT_STATE.md` | 修改 | 回填 R7 状态与路线图 |

## 统计

`git diff --stat`（已跟踪文件，提交前工作区）：

```
backend/main.py               | 44 ++++++++++++++++++++++++++++++++++++++---
backend/test_model_catalog.py | 46 +++++++++++++++++++++++++++++++++++++++++++
frontend/src/App.tsx           | 32 ++++++++++++++++++++++++++++--
3 files changed, 117 insertions(+), 5 deletions(-)
```

新增未跟踪文件：`backend/model_identity.py`、`backend/test_model_identity.py`、`docs/TASK_EVIDENCE/TASK-003.1-R7/`。

原始 diff 见 `git-diff-raw.txt`（仅含已跟踪文件的改动；新增文件内容以工作区文件为准）。

## 未改动

- `backend/model_catalog.py`、`backend/workflow_service.py`、`backend/workflow_api.py`、`backend/datadir.py`、`frontend/src/styles.css` 本轮未改。
- main 分支未改动；所有改动落在 dev。
