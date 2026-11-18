# TASK-003.1-R50 证据汇总（轻量化归档）

## 范围

M6 失败/中断任务的手动重试。批量终验节奏，真机验收在阶段收口统一进行。

## 改动

- 后端 `workflow_api`：抽出共享 `_submit_guarded` fail-closed 提交闸门；新增
  `POST /api/workflows/{id}/tasks/{prompt_id}/retry`。
- 重试口径：仅 `failed`/`interrupted` 可重试；`succeeded`/在途/`unknown` 拒绝 409；旧记录与
  历史快照保留，重试生成新 prompt_id 与新快照；远端失败不改旧记录、不自动重试。
- 前端 `WorkflowWorkbench.tsx`：失败/已中断任务项提供「重试」按钮，成功后刷新列表。
- 文档：`docs/ROADMAP.md` R50 段、`PROJECT_STATE.md` 第 60 节。

## 测试结果

- 后端：**220 passed, 1 warning**（`pytest-output.txt`）。
- 前端：`tsc -b && vite build` 绿，`index-CClNSCnw.js 173.99 kB gzip 55.45 kB`（`frontend-build.txt`）。

## 边界 / backlog

- WebSocket 实时进度、队列暂停/恢复、通知、Ollama unload 状态与显存阈值验证留后续切片。
