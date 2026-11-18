# Git 差异说明 — TASK-003.1-R3

原始完整 diff 见 `git-diff-raw.txt`。

## 变更文件

- `backend/workflow_service.py`
  - 新增中转 conditioning 节点标记表、conditioning 输入键名表与 `_is_conditioning_passthrough`。
  - `_trace_api_encoders`：中转节点沿 conditioning 输入继续向上追溯。
  - 新增 `_structure_diff` 结构化递归比对。
  - 写入前/后完整性校验由整对象 `!=` 改为白名单路径结构化 diff。
- `backend/test_workflow_service.py`
  - 新增 5 个回归用例（见 `test-results.md`）。

## 未变更

- `backend/workflow_api.py`、`backend/main.py`、前端源码、数据目录与迁移逻辑。
- 既有 API 契约与错误码保持不变。
