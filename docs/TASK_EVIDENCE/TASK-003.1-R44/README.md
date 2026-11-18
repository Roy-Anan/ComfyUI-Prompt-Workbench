# TASK-003.1-R44 证据汇总（轻量化归档）

## 范围

M6 第六切片：任务取消（待执行出队）与中断（运行中）。批量终验节奏，真机验收在阶段收口统一进行。

## 改动

- `backend/comfy_client.py`：`cancel_pending`（`/queue` delete）、`interrupt_running`（`/interrupt` 定向）。
- `backend/workflow_api.py`：`POST /api/workflows/{id}/tasks/{prompt_id}/cancel`，按本地状态路由，终态/unknown 拒绝，离线或失败不改本地记录。
- `frontend/src/WorkflowWorkbench.tsx`：在途任务取消/中断按钮，操作后刷新校准。
- `backend/test_workflow_tasks.py`：6 个用例。
- 文档：`docs/ROADMAP.md` R44 段、`PROJECT_STATE.md` 第 54 节。

## 口径

- 终态与 unknown 不臆造操作；远端失败不自动重试；接口形状核对自真机 ComfyUI 0.30.2 源码。

## 测试结果

- 后端：**203 passed, 1 warning in 16.12s**（`pytest-output.txt`；遗留 StarletteDeprecationWarning）。
- 前端：`tsc -b && vite build` 绿，`index-CGPpLaRC.js 169.61 kB gzip 54.44 kB`（`frontend-build.txt`）。

## 边界 / backlog

- 队列暂停/恢复、失败重试、WebSocket 实时进度、断线恢复状态机、通知与图库视图留后续切片。
