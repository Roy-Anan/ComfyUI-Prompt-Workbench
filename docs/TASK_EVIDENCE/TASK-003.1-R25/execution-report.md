# R25 执行报告

## 1. 背景

`_sampler_actuals` 原先只取首个有参数的采样器组并 `break`，多采样器组工作流中其余组被静默丢弃。本切片保守标注全部组，比对主链路仍只对应首组。

## 2. 实施步骤

1. `workflow_api._sampler_actuals` 遍历 `prompt_groups`，收集 `sampler_groups`（`sampler_node_id` + `params`）；首组有参数时其参数写入顶层 actuals。
2. actuals 新增 `sampler_group_count`（组数）与 `sampler_groups`（摘要列表）。
3. 比对层判定口径不变；未新增逐组比对或合并逻辑。
4. 补接口测试：双 KSampler 组（steps 20 / 30），断言顶层取首组、`sampler_groups` 含两组。

## 3. 真机核对

脚本：`smoke_groups.py`（会话临时目录）。

- 导入 PonyDiffusion 档案 20 条、0 拒绝。
- 构造双 KSampler 工作流：节点 7 steps 25 cfg 7.0，节点 9 steps 30 cfg 6.0。
- actuals：顶层 `steps=25, cfg=7.0`；`sampler_group_count=2`；`sampler_groups` 依次为 25/7.0、30/6.0。
- 计数 unknown 19 / match 1；清理后规则表 0 条。

原始样本：`samples/smoke-multi-groups.json`。

## 4. 进程与数据

- 冒烟后回收后端进程，17890 释放；Ollama / ComfyUI 未触碰。
- userdata 工作流副本与真机库为运行时产物，未入库；规则表已归零。

## 5. 未做

- 逐采样器组独立比对、组间参数冲突提示；多 latent 节点取舍在后续切片。
