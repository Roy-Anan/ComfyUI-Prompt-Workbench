# TASK-003.1-R48 证据汇总（轻量化归档）

## 范围

前端生成历史只读面板。批量终验节奏，真机验收在阶段收口统一进行。

## 改动

- `frontend/src/HistoryPanel.tsx`（新）：历史列表与详情展开，展示时间/状态/正向摘要/模型快照/图片存在标记。
- `frontend/src/App.tsx`：接入「生成历史」导航页。
- 文档：`docs/ROADMAP.md` R48 段、`PROJECT_STATE.md` 第 58 节。

## 口径

- 只读视图；图片存在性沿用后端 `exists`（存在/丢失/目录未配置），不复制原图。

## 测试结果

- 后端：**215 passed, 1 warning in 17.09s**（`pytest-output.txt`；本批后端无改动）。
- 前端：`tsc -b && vite build` 绿，`index-BHp-6yRK.js 172.58 kB gzip 55.14 kB`（`frontend-build.txt`）。

## 边界 / backlog

- 缩略图索引、图库网格视图、搜索筛选导出、历史反向创建草稿留后续切片。
