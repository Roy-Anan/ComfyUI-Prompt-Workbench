# R26 测试结果

## 后端

- 命令：`.venv\Scripts\python.exe -m pytest -q`（backend）
- 结果：**164 passed, 1 warning in 6.14s**（本切片未改后端逻辑，回归全绿）

唯一 warning：StarletteDeprecationWarning（既有遗留，未改）。

## 前端

- 命令：`npm run build`（`tsc -b && vite build`）
- 结果：exit 0；`index-BUphuMzW.js 158.94 kB │ gzip 51.58 kB`，CSS 6.54 kB；TypeScript 类型检查通过。

## 真机浏览器

- 工作流：`r26-compare.json`（构造 API 样本）。
- 比对载荷：`samples/compare-payload.json`，counts `{unknown: 18, match: 2}`。
- 截图：`screenshots/compare-panel-meta.png`（头部 + 摘要 + 匹配条目）、`screenshots/compare-entries.png`（条目列表）。
