# TASK-003.1-R54 证据汇总（轻量化归档）

## 范围

M5 版本快照只读列表。批量终验节奏，真机验收在阶段收口统一进行。

## 改动

- 后端 `workflow_service.py`：新增 `list_versions(workflow_id)`，扫描 `versions/*.json` 按时间戳
  降序，按白名单提取快照正/负 Prompt 文本；损坏快照保守跳过；不提供恢复动作。
- 后端 `workflow_api.py`：新增只读端点 `GET /api/workflows/{workflow_id}/versions`，返回
  `{"items": [...]}`；未知工作流 404。
- 前端 `WorkflowWorkbench.tsx`：详情面板新增「历史版本（只读）」小节，展示版本时间与正/负
  Prompt 摘要，无恢复/差异按钮。
- 测试：service 层版本顺序与快照文本用例；端点层空列表 200、未知工作流 404 用例。
- 文档：`docs/ROADMAP.md` R54 段、`PROJECT_STATE.md` 第 64 节。

## 测试结果

- 后端：**224 passed, 1 warning**（`pytest-output.txt`）。
- 前端：`tsc -b && vite build` 绿，`index-vwJ__kjB.js 176.08 kB gzip 56.11 kB`
  （`frontend-build.txt`）。

## 边界 / backlog

- 版本恢复、差异比对、备注、标签收藏、多草稿与草稿箱留后续切片；当前仅只读列表。
