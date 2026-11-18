# R27 测试结果

## 后端

- 命令：`.venv\Scripts\python.exe -m pytest -q`（backend）
- 结果：**164 passed, 1 warning in 6.03s**

唯一 warning：StarletteDeprecationWarning（既有遗留，未改）。

## 前端

- 命令：`npm run build`（`tsc -b && vite build`）
- 结果：exit 0；`index-DX9kN6tt.js 160.40 kB │ gzip 51.89 kB`，CSS 6.85 kB；TypeScript 类型检查通过。

## 真机浏览器

- 工作流：`r27-multi-group.json`（双组构造 API 样本）。
- 载荷：`samples/compare-payload.json`。
  - 顶层（首组）counts `{unknown: 18, match: 2}`。
  - 组 7：steps 25 / cfg 7.0，counts `{unknown: 18, match: 2}`。
  - 组 9：steps 30 / cfg 6.0，counts `{unknown: 18, match: 1, out_of_range: 1}`。
- 截图：`screenshots/compare-group1.png`、`screenshots/compare-group2.png`。
