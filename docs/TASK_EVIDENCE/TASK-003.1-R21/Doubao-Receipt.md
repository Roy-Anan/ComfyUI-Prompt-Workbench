# Doubao 回执 — TASK-003.1-R21

## 任务

M3 第十六切片：参数值剥离尾部备注后再结构化解析。带括号适用条件/示例说明的值不再整段回退原文；核心值走既有结构化，原值保留可追溯。

## 完成内容

- `backend/value_normalize.py`：`_strip_trailing_parenthetical()` 剥离尾部括号备注；`normalize()` 清洗副本解析、raw 保留原值；`normalize_list()` 单值归单元素列表。
- `backend/test_value_normalize.py`：备注剥离、单值列表、分号两套建议不混并。
- `backend/test_rule_compare.py`：剥离备注后的 Scheduler 规则与实际 karras 命中。
- 文档：`PROJECT_STATE.md` 第 31 节、`docs/ROADMAP.md` 回填 R21。

## 自测结果

- 后端：**151 passed, 1 warning in 5.88s**。
- 前端：`tsc -b && vite build` exit 0；`index-IXKUmsZF.js 156.95 kB`、CSS 5.44 kB。
- 真机冒烟（`samples/smoke-notes.json`）：
  - 导入 IntoRealism 档案 17 条、0 拒绝。
  - Scheduler `Karras（Euler A 时）`→list ["Karras"]，提示载荷 resolved；Steps `6~12` range、CFG `1.5~2` range、Sampler list 两项保持结构化。
  - 清理后规则表 0 条。

## 保守边界

- 只剥离尾部括号；括号内含关键参数、分号第二套建议不拆分。
- `35；25~40` 这类示例/指南两套并存仍留 unstructured，未臆造合并。

## Git

- 功能提交：`45fee397fa7cd47e6a4b2e6a303c78f8798a62f3`（本地 dev，已推送 origin/dev）。
- 远端核对：连接器 `list_commits(dev)` 最新提交即 `45fee39`，消息「feat(rules): M3 第十六切片参数值剥离尾部备注后再结构化解析」，作者 Roy-Anan / 1538072315@qq.com。
- main 分支未改动。

## 边界

- 两套建议分组结构化、Resolution 括号内尺寸提取、Resolution 与 latent 尺寸对接在后续切片。
