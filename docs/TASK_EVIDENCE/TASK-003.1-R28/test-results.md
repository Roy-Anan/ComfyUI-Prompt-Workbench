# R28 测试结果

## 后端

- 命令：`.venv\Scripts\python.exe -m pytest -q`（backend）
- 结果：**164 passed, 1 warning in 6.15s**（本切片无后端逻辑改动，回归全绿）

唯一 warning：StarletteDeprecationWarning（既有遗留，未改）。

## 前端

- 命令：`npm run build`（`tsc -b && vite build`）
- 结果：exit 0；`index-8q4qtSIr.js 161.93 kB │ gzip 52.39 kB`，CSS 7.64 kB；TypeScript 类型检查通过。

## 真机浏览器

- 工作流/档案：`PonyDiffusion_V6_XL.txt` 导入 20 条。
- 载荷：`samples/rules-payload.json`，checkpoint 15 / architecture 5 / global 0。
- 截图：`screenshots/rules-checkpoint-group.png`（模型档案分组）、`rules-architecture-group.png`（架构基线分组）。
