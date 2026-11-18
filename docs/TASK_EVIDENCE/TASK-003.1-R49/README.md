# TASK-003.1-R49 证据汇总（轻量化归档）

## 范围

M7 生成历史记录的只读筛选。批量终验节奏，真机验收在阶段收口统一进行。

## 改动

- 后端 `generation_history.list_history`：新增 `status`（任务状态精确匹配）、`keyword`
  （大小写不敏感，匹配正/负向 Prompt 文本与冻结模型快照文件名）过滤；LIKE 通配符转义。
- 后端 `/api/history`：透传 `status`、`keyword` 查询参数。
- 前端 `HistoryPanel.tsx`：状态下拉、工作流下拉（现有记录派生）、关键词输入，本地即时筛选；
  无匹配独立空态。
- 样式 `styles.css`：筛选行布局。
- 文档：`docs/ROADMAP.md` R49 段、`PROJECT_STATE.md` 第 59 节。

## 口径

- 只读过滤；未知状态精确匹配为空，不重映射、不臆测；空筛选条件忽略。
- 关键词同时覆盖 Prompt 文本与模型快照 JSON 中的文件名。

## 测试结果

- 后端：**216 passed, 1 warning**（`pytest-output.txt`）。
- 前端：`tsc -b && vite build` 绿，`index-B1NYoJeQ.js 173.69 kB gzip 55.39 kB`（`frontend-build.txt`）。

## 边界 / backlog

- 缩略图索引、图库网格视图、日期范围与导出、历史反向创建草稿留后续切片。
