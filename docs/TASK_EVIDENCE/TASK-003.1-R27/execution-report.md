# R27 执行报告

## 1. 背景

R25 已把多采样器组参数列入 `sampler_groups`，但顶层比对只取首组，其余组被静默跳过。本切片补齐逐组独立比对，并在前端分组呈现。

## 2. 实施步骤

1. `rule_compare.py`：抽出 `_count`；`compare_workflow` 遍历 `actuals["sampler_groups"]`，每组以公共事实（width/height/clip_skip）叠加本组 params 生成组 actuals，独立跑 `compare_rule`，输出 `{sampler_node_id, params, comparisons, counts}`。
2. 测试：种子 Steps 规则补结构化 `{kind: value, value: 20}`；双组工作流断言首组 Steps match、次组 out_of_range，分组计数互不串扰。
3. 前端：新增 `GroupComparison` 类型；多组时渲染「逐采样器组比对」小节，每组卡片含节点、步数/CFG/采样器/调度器摘要、分组计数徽标与条目列表。

## 3. 真机核对

- 前置：导入 `ponyDiffusionV6XL_v6.safetensors` 档案 20 条；构造双组 API 工作流：节点 7 KSampler steps 25 cfg 7.0，节点 9 KSampler steps 30 cfg 6.0，latent 832×1216，CLIPSetLastLayer -2。
- 后端 compare：顶层 counts `{unknown:18, match:2}`（首组）；组 7 counts `{unknown:18, match:2}`；组 9 counts `{unknown:18, match:1, out_of_range:1}`。
- 浏览器：组 1 节点 7 步数 25 / CFG 7 / 匹配 2；组 2 节点 9 步数 30 / CFG 6 / 匹配 1 / 超出范围 1。
- 截图：`screenshots/compare-group1.png`、`screenshots/compare-group2.png`；载荷 `samples/compare-payload.json`。
- 清理后规则表 0 条。

## 4. 进程与数据

- 验收后回收后端进程，17890 释放；Ollama / ComfyUI 未触碰。
- userdata 工作流副本与真机库为运行时产物，未入库；规则表已归零。

## 5. 未做

- 跨组参数冲突裁决、推荐取值；多组规则组合（LoRA 等）为后续切片。
