# R31 Git Diff 摘要

基线：`afe9a9f`（R30 回执提交）。本切片未触碰 `main`。

## 改动统计

```
 frontend/src/App.tsx               |  5 +++--
 frontend/src/WorkflowWorkbench.tsx |  7 +------
 frontend/src/format.ts             | 新增（共享格式化工具）
 2 files changed, 4 insertions(+), 8 deletions(-)
```

## 改动要点

### `frontend/src/format.ts`（新增）

- `formatStructured(value)`：带 kind 的 structured 记录摘要——`value` 原样、`range` `low~high`、`floor` `≥low`、`resolutions` 尺寸以 `/` 连接、`list` 项以 `/` 连接；未知形态回退 JSON。
- `formatActual(value)`：比对 verdict 提炼值兼容——数值/字符串、`{low,high}`、`{floor}`、分辨率对、分辨率数组、普通列表数组；其余回退 JSON。

### `frontend/src/App.tsx`

- 引入 `formatStructured`；规则库面板与档案候选面板的 `structured` 字段由 `formatRuleValue`（JSON）改为 `formatStructured`（可读摘要）。原始 `value` 展示不变。

### `frontend/src/WorkflowWorkbench.tsx`

- 删除本地 `formatActual`（原实现对象一律 `JSON.stringify`），改为从 `format.ts` 导入共享实现。

完整补丁（含新增 `format.ts` 全文）见 `git-diff-raw.txt`。
