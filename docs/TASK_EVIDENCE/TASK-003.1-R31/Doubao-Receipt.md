# Doubao 回执 — TASK-003.1-R31

## 任务

M3 第二十六切片：结构化规则值前端可读摘要。此前规则库、档案候选、比对面板对结构化值与 verdict 提炼值一律 `JSON.stringify`，界面出现原始对象；本切片抽出共享格式化工具渲染可读摘要，纯展示层，不改后端归一化与比对结论。

## 完成内容

- `frontend/src/format.ts`（新增）：`formatStructured`（value/range/floor/resolutions/list）与 `formatActual`（数值、`{low,high}`、`{floor}`、分辨率对/数组、列表数组）；未知形态回退 JSON。
- `frontend/src/App.tsx`：规则库与档案候选面板 `structured` 字段改用 `formatStructured`。
- `frontend/src/WorkflowWorkbench.tsx`：删除本地 `formatActual`，改用共享实现。
- 文档：`PROJECT_STATE.md` 第 41 节、`docs/ROADMAP.md` 回填 R31。
- 后端零改动。

## 口径

- 摘要仅用于展示；后端 `structured` 记录、比对 verdict 与计数未改动。
- `structured=None` 显示「—」；未知形态回退原始 JSON，不补造数值。

## 自测结果

- 后端：**165 passed, 1 warning in 6.04s**。
- 前端：`tsc -b && vite build` exit 0；`index-D68eGJQw.js 165.08 kB │ gzip 53.22 kB`，CSS 8.09 kB。
- 真机浏览器：规则库 value/range/floor/resolutions/list 五类摘要正确（CFG 5、Steps 30~32、CFG 4~6、Steps ≥30、分辨率与采样器列表）；比对面板规则列数值/分辨率/列表/下限摘要正确。截图 `screenshots/rules-summary.png`、`screenshots/compare-summary.png`；载荷 `samples/compare-payload.json`。
- 清理后规则表 0 条；后端进程已回收，17890 端口释放。

## Git

- 功能提交：见下方回填。
- 回执提交：见下方回填。
- main 分支未改动。

## 边界

- 分号两套建议分组结构化与示例套/推荐套优先级语义留后续切片；本切片摘要只服务既有 kind。
