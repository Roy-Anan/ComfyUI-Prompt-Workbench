# TASK-003.1-R51 证据汇总（轻量化归档）

## 范围

M7 历史记录导出：把当前筛选结果导出为本地 JSON。批量终验节奏，真机验收在阶段收口统一进行。

## 改动

- 前端 `HistoryPanel.tsx`：新增「导出 JSON」按钮，将当前状态/工作流/关键词筛选后的记录经前端
  Blob 下载为 `workbench-history-<时间戳>.json`，含导出时间、条数与完整记录；仅记录文件名与
  存在性，不复制原图。无新增后端端点。
- 文档：`docs/ROADMAP.md` R51 段、`PROJECT_STATE.md` 第 61 节。

## 测试结果

- 后端：无改动，沿用 **220 passed, 1 warning** 基线（`pytest-output.txt` 复跑确认）。
- 前端：`tsc -b && vite build` 绿，`index-DHO60mp6.js 174.51 kB gzip 55.66 kB`（`frontend-build.txt`）。

## 边界 / backlog

- 缩略图索引、图库网格视图、日期范围导出、历史反向创建草稿留后续切片。
