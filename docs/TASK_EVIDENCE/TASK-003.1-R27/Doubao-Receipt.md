# Doubao 回执 — TASK-003.1-R27

## 任务

M3 第二十二切片：多采样器组逐组比对。R25 已列出各组参数但顶层比对只取首组，本切片补齐逐组独立比对并在前端分组呈现。

## 完成内容

- `backend/rule_compare.py`：抽出 `_count`；`compare_workflow` 新增 `sampler_group_comparisons`，每组以公共事实（latent 宽高、Clip Skip）叠加本组 params 独立比对，返回 `{sampler_node_id, params, comparisons, counts}`。
- `backend/test_workflow_rules.py`：种子 Steps 规则补结构化 `{kind: value, value: 20}`；双组工作流断言首组 match、次组 out_of_range，分组计数独立不串扰。
- `frontend/src/WorkflowWorkbench.tsx`：`GroupComparison` 类型与「逐采样器组比对」分组卡片（节点、参数摘要、分组计数、条目列表）。
- `frontend/src/styles.css`：分组卡片样式。
- 文档：`PROJECT_STATE.md` 第 37 节、`docs/ROADMAP.md` 回填 R27。

## 口径

- 顶层 `comparisons` / `counts` 仍对应首组；逐组结论在 `sampler_group_comparisons`。
- 组间参数不合并、不替选；跨组冲突裁决不在本切片。

## 自测结果

- 后端：**164 passed, 1 warning in 6.03s**。
- 前端：`tsc -b && vite build` exit 0；`index-DX9kN6tt.js 160.40 kB │ gzip 51.89 kB`。
- 真机浏览器（`samples/compare-payload.json`）：
  - 顶层（首组）counts `{unknown: 18, match: 2}`。
  - 组 7：steps 25 / cfg 7.0，counts `{unknown: 18, match: 2}`。
  - 组 9：steps 30 / cfg 6.0，counts `{unknown: 18, match: 1, out_of_range: 1}`。
  - 截图 `screenshots/compare-group1.png`、`screenshots/compare-group2.png`；清理后规则表 0 条。

## Git

- 功能提交：`39aa566b4ad3fae7c4b863dc4910933453c337b2`（本地 dev，已推送 origin/dev）。
- 远端核对：连接器 `list_commits(dev)` 最新提交即 `39aa566`，消息「feat(rules): M3 第二十二切片 多采样器组逐组比对」，作者 Roy-Anan / 1538072315@qq.com。
- main 分支未改动。

## 边界

- 跨组冲突只逐组呈现，未做裁决或推荐取值；LoRA / 多模型规则组合与冲突人工处理界面为后续切片。
