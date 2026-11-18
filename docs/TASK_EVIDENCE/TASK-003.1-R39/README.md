# TASK-003.1-R39 证据汇总（轻量化归档）

## 范围

M6 第一切片：ComfyUI 连接与设备显存状态只读解析。批量终验节奏，真机验收在阶段收口统一进行。

## 改动

- `backend/main.py`：新增 `fetch_comfyui_status` 与 `GET /api/comfyui/status`，只读解析 `/system_stats`。
- `backend/test_main.py`：端点透传、离线透传、不可达主机容错、混合类型结构解析容错共 4 个用例。
- 文档：`docs/ROADMAP.md` R39 段、`PROJECT_STATE.md` 第 49 节。

## 口径

- 离线/超时/坏 JSON/结构不符记 `unknown`（字段 `None`、设备空列表），不臆测数值。
- 只读探测，不提交任务、不控制 ComfyUI 进程。

## 测试结果

- 后端：**180 passed, 1 warning in 10.75s**（`pytest-output.txt`；遗留 StarletteDeprecationWarning）。
- 前端：本批无源码改动，未重新构建。

## 边界 / backlog

- 队列调度、任务 HTTP 提交、WebSocket 进度、断线恢复、显存与 LLM 卸载互斥判断留后续切片。
