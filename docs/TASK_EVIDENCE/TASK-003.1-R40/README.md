# TASK-003.1-R40 证据汇总（轻量化归档）

## 范围

M6 第二切片：ComfyUI 队列与历史只读探测。批量终验节奏，真机验收在阶段收口统一进行。

## 改动

- `backend/main.py`：新增 `fetch_comfyui_queue` 与 `GET /api/comfyui/queue`，只读投影队列/历史 prompt 标识。
- `backend/test_main.py`：端点透传、离线透传、不可达主机容错、混合类型标识解析容错共 4 个用例。
- 文档：`docs/ROADMAP.md` R40 段、`PROJECT_STATE.md` 第 50 节。

## 口径

- 只读探测，不提交、不取消、不调整队列；离线/结构不符保守空列表，不臆造 id。

## 测试结果

- 后端：**184 passed, 1 warning in 15.10s**（`pytest-output.txt`；遗留 StarletteDeprecationWarning）。
- 前端：本批无源码改动，未重新构建。

## 边界 / backlog

- 任务提交、提交前显存/LLM 卸载闸门、WebSocket 进度、断线恢复与中断任务不自动重出留后续切片。
