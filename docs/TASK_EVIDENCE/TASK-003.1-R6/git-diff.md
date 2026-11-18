# Git Diff 说明 — TASK-003.1-R6

## 改动概览

| 文件 | 类型 | 说明 |
| --- | --- | --- |
| `backend/model_catalog.py` | 新增 | 只读模型清单分组、目录存在性核对、不可达容错 |
| `backend/test_model_catalog.py` | 新增 | 5 例后端回归用例 |
| `backend/main.py` | 修改 | 新增 `GET /api/models/catalog` 路由，接入设置中的 ComfyUI 地址与外部目录 |
| `frontend/src/App.tsx` | 修改 | 清单类型、并行拉取、只读清单面板与存在性标签 |
| `frontend/src/styles.css` | 修改 | 清单三列响应式布局与列表样式 |

## 统计

`git diff --stat`（已跟踪文件）：

```
backend/main.py         | 20 ++++++++++
frontend/src/App.tsx    | 97 ++++++++++++++++++++++++++++++++++++++++++++++++-
frontend/src/styles.css | 69 +++++++++++++++++++++++++++++++++++
3 files changed, 185 insertions(+), 1 deletion(-)
```

新增未跟踪文件：`backend/model_catalog.py`、`backend/test_model_catalog.py`、`docs/TASK_EVIDENCE/TASK-003.1-R6/`。

原始 diff 见 `git-diff-raw.txt`（仅含已跟踪文件的改动；新增文件内容以工作区文件为准）。

## 未改动

- `backend/workflow_service.py`、`backend/workflow_api.py`、`backend/datadir.py` 本轮未改。
- main 分支未改动；所有改动落在 dev。
