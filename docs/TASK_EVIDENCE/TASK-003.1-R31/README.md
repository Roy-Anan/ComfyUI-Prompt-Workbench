# TASK-003.1-R31 M3 第二十六切片：结构化规则值前端可读摘要

## 范围

把规则库、旧档案候选、规则比对三处前端展示里直接 `JSON.stringify` 的结构化值，替换为可读中文摘要。纯展示层改动，不改变后端归一化与比对结论口径。

## 改动文件

- `frontend/src/format.ts`（新增）：`formatStructured`（带 kind 的 structured：value/range/floor/resolutions/list）与 `formatActual`（比对 verdict 提炼值：数值、`{low,high}`、`{floor}`、分辨率对/数组、列表数组）。
- `frontend/src/App.tsx`：规则库与档案候选面板的 `structured` 字段改用 `formatStructured`。
- `frontend/src/WorkflowWorkbench.tsx`：删除本地 `formatActual`，改用共享实现。
- 后端零改动。

## 摘要口径

| 结构化 kind | 渲染 |
| --- | --- |
| `value` | 数值原样 |
| `range` | `low~high` |
| `floor` | `≥low` |
| `resolutions` | `832×1216 / 768×1152` |
| `list` | `项 A / 项 B` |
| 未知形态 | 回退原始 JSON，不臆测 |

## 验收结论

- 后端 pytest：165 passed, 1 warning in 6.04s。
- 前端构建：exit 0；`index-D68eGJQw.js 165.08 kB`（gzip 53.22 kB），CSS 8.09 kB。
- 真机：规则库 value/range/floor/resolutions/list 五类摘要正确；比对面板规则列数值、分辨率、采样器列表、下限摘要正确。
- 清理后规则表 0 条。

## 证据清单

- `samples/compare-payload.json`：比对 verdict 载荷。
- `screenshots/rules-summary.png`：规则库结构化摘要。
- `screenshots/compare-summary.png`：比对面板规则列摘要。
- `pytest-output.txt` / `frontend-build.txt` / `git-diff.md` / `git-diff-raw.txt` / `known-issues.md`。
