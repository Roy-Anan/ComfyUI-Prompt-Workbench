# Doubao 回执 — TASK-003.1-R25

## 任务

M3 第二十切片：多采样器组 actuals 保守标注。原 `_sampler_actuals` 只取首个有参数的组并中断，其余组被静默丢弃；本切片列出全部组，比对主链路仍对应首组。

## 完成内容

- `backend/workflow_api.py`：遍历 `prompt_groups`，actuals 新增 `sampler_group_count` 与 `sampler_groups`（每组 node_id + params 摘要）；顶层 actuals 取首个有参数的组。
- 测试：`test_workflow_rules.py` 双 KSampler 组样本断言。
- 文档：`PROJECT_STATE.md` 第 35 节、`docs/ROADMAP.md` 回填 R25。

## 口径

- 多组参数不合并、不替选；判定仅对应首组。
- 逐组独立比对、组间冲突提示为后续切片。

## 自测结果

- 后端：**164 passed, 1 warning in 5.87s**。
- 前端：`tsc -b && vite build` exit 0。
- 真机闭环（`samples/smoke-multi-groups.json`）：
  - 导入 PonyDiffusion 档案 20 条、0 拒绝。
  - 双组：节点 7 steps 25 cfg 7.0，节点 9 steps 30 cfg 6.0。
  - actuals 顶层 steps 25 / cfg 7.0；`sampler_group_count=2`；`sampler_groups` 25/7.0、30/6.0。
  - 计数 unknown 19 / match 1；清理后规则表 0 条。

## Git

- 功能提交：`ecd58342184ceb43119a3f15b2a0a53556953776`（本地 dev，已推送 origin/dev）。
- 远端核对：连接器 `list_commits(dev)` 最新提交即 `ecd5834`，消息「feat(rules): M3 第二十切片 多采样器组 actuals 保守标注」，作者 Roy-Anan / 1538072315@qq.com。
- main 分支未改动。

## 边界

- 次组参数仅在摘要中可见，不参与 match/out_of_range 判定；多 latent 节点取舍未实现。
