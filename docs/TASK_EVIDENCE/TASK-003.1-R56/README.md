# TASK-003.1-R56 证据汇总（轻量化归档）

## 范围

M7 历史日期范围筛选。批量终验节奏，真机验收在阶段收口统一进行。

## 改动

- 前端 `HistoryPanel.tsx`：新增开始/结束日期 state，本地按 `created_at` 日期部分即时过滤，
  与既有状态/工作流/关键词筛选叠加；纯前端，无新增后端端点。

## 测试结果

- 后端：**224 passed, 1 warning**（`pytest-output.txt`，无后端改动，沿用 R54 基线）。
- 前端：`tsc -b && vite build` 绿，`index-Df9yT-1_.js 176.90 kB gzip 56.26 kB`
  （`frontend-build.txt`）。

## 边界 / backlog

- 缩略图索引、时间轴视图、历史反向创建草稿留后续；日期范围仅本地过滤当前已加载记录。
