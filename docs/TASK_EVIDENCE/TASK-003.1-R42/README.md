# TASK-003.1-R42 证据汇总（轻量化归档）

## 范围

M6 第四切片：任务状态从队列/历史回读校准。批量终验节奏，真机验收在阶段收口统一进行。

## 改动

- `backend/comfy_client.py`：`fetch_task_states` 聚合队列运行中/待执行与历史详情（status_str、completed、outputs）。
- `backend/comfy_tasks.py`：`classify_history_status` 保守映射 succeeded/failed/interrupted/unknown。
- `backend/workflow_api.py`：`GET /api/workflows/{id}/tasks?refresh=true` 校准本地记录，离线保留本地状态并返回 sync_error。
- `backend/test_workflow_tasks.py`：5 个校准/容错用例。
- 文档：`docs/ROADMAP.md` R42 段、`PROJECT_STATE.md` 第 52 节。

## 口径

- 队列与历史均找不到的在途任务记 unknown，不直接判失败；不自动重出；未明确报告成功/失败不臆造。

## 测试结果

- 后端：**197 passed, 1 warning in 15.61s**（`pytest-output.txt`；遗留 StarletteDeprecationWarning）。
- 前端：本批无源码改动，未重新构建。

## 边界 / backlog

- WebSocket 进度订阅、队列暂停/恢复/取消/重试、断线恢复状态机、中断任务界面与通知留后续切片。
