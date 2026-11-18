# TASK-003.1-R41 证据汇总（轻量化归档）

## 范围

M6 第三切片：ComfyUI 任务提交后端与本地记录。批量终验节奏，真机验收在阶段收口统一进行。

## 改动

- `backend/comfy_client.py`：ComfyUI/Ollama 只读探测与受控 `/prompt` 提交，无云端回退。
- `backend/comfy_tasks.py`：`comfy_task` 表持久化提交记录与状态枚举。
- `backend/workflow_service.py`：`read_working()` 读取工作副本。
- `backend/workflow_api.py`：`POST /api/workflows/{id}/tasks`、`GET /api/workflows/{id}/tasks`。
- `backend/test_workflow_tasks.py`：8 个闸门/落库/容错用例。
- 文档：`docs/ROADMAP.md` R41 段、`PROJECT_STATE.md` 第 51 节。

## 口径

- fail-closed：ComfyUI 不可达、UI 格式、白名单未确认、LLM 状态不可确认或仍驻留、节点校验错误均拒绝；失败不写记录、不自动重试。
- 未拍板的显存数值阈值与互斥放宽口径不臆造；本批只做"无法确认即拒绝"。

## 测试结果

- 后端：**192 passed, 1 warning in 15.31s**（`pytest-output.txt`；遗留 StarletteDeprecationWarning）。
- 前端：本批无源码改动，未重新构建。

## 边界 / backlog

- 队列调度（暂停/恢复/取消/重试）、WebSocket 进度、queue/history 状态回读校准、断线恢复与中断任务界面留后续切片。
