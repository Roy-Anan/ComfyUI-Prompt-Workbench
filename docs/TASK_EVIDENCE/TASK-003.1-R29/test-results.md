# R29 测试结果

## 后端

- 命令：`.venv\Scripts\python.exe -m pytest -q`（backend）
- 结果：**165 passed, 1 warning in 6.03s**（新增 1 条双节点解析用例，其余回归全绿）

唯一 warning：StarletteDeprecationWarning（既有遗留，未改）。

## 前端

- 命令：`npm run build`（`tsc -b && vite build`）
- 结果：exit 0；`index-BaTB97FZ.js 162.27 kB │ gzip 52.51 kB`，CSS 7.64 kB；TypeScript 类型检查通过。
- 首轮构建两处 TS2322（unknown 不能赋 ReactNode），计数文案经 `formatActual` 显式格式化后通过。

## 真机浏览器

- 工作流：双 latent（6: 832×1216、10: 768×1152）、双 CLIPSetLastLayer（8: -2、11: -3）。
- 载荷：`samples/compare-payload.json`；`latent_node_count=2`、`clip_skip_node_count=2`。
- 截图：`screenshots/compare-multi-nodes.png`。
