# TASK-003.1-R55 证据汇总（轻量化归档）

## 范围

M9 设置只读导出。批量终验节奏，真机验收在阶段收口统一进行。

## 改动

- 前端 `App.tsx`：设置页新增「导出设置」按钮，将当前已加载设置按白名单
  （`version/storage/connections`）经 Blob 下载 `workbench-settings-<时间戳>.json`。
- 导出内容仅本地目录与回环连接地址；不含模型权重、原图、历史记录或遗留杂项。
- 纯前端，复用既有 `GET /api/settings`，无新增后端端点。

## 测试结果

- 后端：**224 passed, 1 warning**（`pytest-output.txt`，无后端改动，沿用 R54 基线）。
- 前端：`tsc -b && vite build` 绿，`index-lDUuS2TQ.js 176.57 kB gzip 56.19 kB`
  （`frontend-build.txt`）。

## 边界 / backlog

- 设置导入、整库备份恢复、数据库迁移留后续切片；当前仅只读导出当前配置。
