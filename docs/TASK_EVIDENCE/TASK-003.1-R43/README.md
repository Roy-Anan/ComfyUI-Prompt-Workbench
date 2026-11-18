# TASK-003.1-R43 证据汇总（轻量化归档）

## 范围

M6 第五切片：前端 ComfyUI 任务面板。批量终验节奏，真机验收在阶段收口统一进行。

## 改动

- `frontend/src/WorkflowWorkbench.tsx`：任务面板（提交按钮、任务列表、状态徽章、错误/输出摘要、刷新校准）。
- 文档：`docs/ROADMAP.md` R43 段、`PROJECT_STATE.md` 第 53 节。

## 口径

- 仅 API 格式且白名单已确认可提交；UI 格式提示不可直接提交；状态保守展示，不臆造结果。

## 测试结果

- 后端：**197 passed, 1 warning in 15.56s**（`pytest-output.txt`；遗留 StarletteDeprecationWarning）。
- 前端：`tsc -b && vite build` 绿，`index-CTtb3PIL.js 169.24 kB gzip 54.36 kB`（`frontend-build.txt`）。

## 边界 / backlog

- WebSocket 实时进度、队列暂停/恢复/取消/重试、断线恢复状态机、中断通知与图库视图留后续切片。
