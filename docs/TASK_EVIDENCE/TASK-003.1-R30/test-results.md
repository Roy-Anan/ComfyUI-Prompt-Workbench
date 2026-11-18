# R30 测试结果

## 后端 pytest

- 命令：`backend/  python -m pytest -q`
- 结果：**165 passed, 1 warning in 6.10s**
- 说明：本切片后端零改动；165 条既有回归全部通过。遗留 `StarletteDeprecationWarning` 与本切片无关。
- 原始输出：`pytest-output.txt`

## 前端构建 / 类型检查

- 命令：`frontend/  npm run build`（`tsc -b && vite build`）
- 结果：exit 0
- 产物：`index-Cw2T345o.js 164.26 kB │ gzip 52.99 kB`，`index-DkENSQMT.css 8.09 kB`
- 原始输出：`frontend-build.txt`

## 真机冒烟（浏览器只读验收）

| 检查点 | 结果 |
| --- | --- |
| `GET /api/profiles` 返回 13 份档案 | 通过 |
| 档案行展示文件名 / 架构 / 候选数 / 未识别字段数 | 通过 |
| 展开调用 `GET /api/profiles/Anything_V5.txt`，返回 12 条候选 | 通过 |
| 候选展示层级标签、作用域、值、备注、来源/可信度/版本标签 | 通过 |
| 面板无导入 / 勾选 / 驳回写控件 | 通过 |
| 规则表 `workbench_rule` 计数 0 | 通过 |
