# R31 执行报告

## 任务

此前前端对结构化规则值与比对 verdict 提炼值一律 `JSON.stringify`，界面上出现 `{"kind":"range","low":30,"high":32}`、`{"floor":30}` 这类原始对象。本切片抽出共享格式化工具，渲染为可读摘要；只改展示，不改后端解析与比对结论。

## 实施步骤

1. 盘点三处展示点：`App.tsx` 规则库面板、`App.tsx` 档案候选面板、`WorkflowWorkbench.tsx` 比对面板。
2. 新增 `frontend/src/format.ts`：
   - `formatStructured`：按 `kind` 渲染 value/range/floor/resolutions/list；未知形态回退 JSON。
   - `formatActual`：兼容比对 verdict 提炼值——纯数值/字符串、`{low,high}`、`{floor}`、分辨率对、分辨率数组、普通列表数组；其余回退 JSON。
3. `App.tsx` 引入 `formatStructured`，两处 `structured` 展示替换；原始 `value` 仍走既有 `formatRuleValue`。
4. `WorkflowWorkbench.tsx` 删除本地 `formatActual`，改为从 `format.ts` 导入。
5. 后端回归、前端构建；真机导入两份覆盖五类结构化的档案，核对规则库摘要；构造 CyberRealisticPony 工作流跑比对，核对规则列摘要。
6. 清理导入规则（归零），回收后端进程。

## 口径核对

- 摘要仅用于展示；后端 `structured` 记录、比对 verdict 与计数均未改动。
- 解析失败仍为 `structured=None`，界面显示「—」，不补造摘要。

## 结果

- 规则库真机：CFG `5`、Resolution `896×1152 / 832×1216`、Sampler `DPM++ SDE Karras / …`、Steps `≥30`、Steps `30~32`、CFG `4~6`。
- 比对面板真机：Clip Skip `2`、CFG `5`、Resolution `896×1152 / 832×1216`、Sampler 列表、Steps `≥30`。
- 进程回收：父 PID 20092、uvicorn 子 PID 23208 已回收，17890 释放；规则表 0 条。
