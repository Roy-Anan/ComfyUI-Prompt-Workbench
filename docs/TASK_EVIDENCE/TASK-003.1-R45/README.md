# TASK-003.1-R45 证据汇总（轻量化归档）

## 范围

M6 第七切片：LLM 与 ComfyUI 互斥反向闸门。批量终验节奏，真机验收在阶段收口统一进行。

## 改动

- `backend/comfy_client.py`：`queue_has_active_task`（在线且 running/pending 非空记 active；离线记无在途）。
- `backend/workflow_api.py`：候选生成调本地 LLM 前查队列，在途任务 409 拒绝；空闲/离线放行。
- `backend/test_workflow_tasks.py`：3 个用例（活动拒绝不调 chat、空闲放行、离线放行）。
- 文档：`docs/ROADMAP.md` R45 段、`PROJECT_STATE.md` 第 55 节。

## 口径

- 离线视为 ComfyUI 未运行、不可能持有在途任务，不阻断候选生成；不臆造显存阈值。

## 测试结果

- 后端：**206 passed, 1 warning in 16.23s**（`pytest-output.txt`；遗留 StarletteDeprecationWarning）。

## 边界 / backlog

- 显存数值阈值、Ollama 主动 unload、WebSocket 进度、队列暂停/恢复/重试、断线恢复留后续切片。
