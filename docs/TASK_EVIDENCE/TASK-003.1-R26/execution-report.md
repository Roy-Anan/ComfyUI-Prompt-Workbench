# R26 执行报告

## 1. 背景

后端比对链路（R19–R25）已能产出规则/实际参数结论，但前端工作区只展示模型与 LoRA 节点，比对结果不可见。本切片把 compare 载荷以只读面板呈现。

## 2. 实施步骤

1. `WorkflowWorkbench.tsx` 新增 `ComparisonEntry` / `ComparePayload` 类型与 `compare` 状态；`loadCompare(id)` 拉取 `/api/workflows/{id}/rules/compare`，在打开工作流与导入成功后调用。
2. 面板展示：
   - 头部：注册状态（已登记/未登记）、Checkpoint、架构标签；
   - 计数徽标：match / out_of_range / out_of_set / unknown；
   - 实际参数摘要：步数、CFG、采样器、调度器、Clip Skip、分辨率；
   - 比对条目：规则键、规则值、实际值、状态徽标与理由。
3. 未登记工作流显示提示，不猜测参数。
4. `styles.css` 补面板布局与三档状态配色。

## 3. 真机核对

- 前置：导入 `ponyDiffusionV6XL_v6.safetensors` 档案 20 条；构造 API 工作流（KSampler steps 25 cfg 7.0、latent 832×1216、CLIPSetLastLayer -2）。
- 浏览器打开工作台 → 工作流工作区 → 打开 `r26-compare.json`。
- 面板：状态已登记；Checkpoint ponyDiffusionV6XL_v6.safetensors；架构 Pony / SDXL 系；计数 unknown 18 / match 2；摘要步数 25、CFG 7、Clip Skip 2、分辨率 832×1216。
- 匹配条目：`ARCHITECTURE::Clip Skip` 规则 2 / 实际 2；`GENERATION SETTINGS::Steps` 规则 25 / 实际 25；其余条目为 unknown 并带理由（field_not_compared / rule_not_structured / actual_missing）。
- 截图：`screenshots/compare-panel-meta.png`、`screenshots/compare-entries.png`；载荷 `samples/compare-payload.json`。
- 清理后规则表 0 条。

## 4. 进程与数据

- 验收后回收后端进程，17890 释放；Ollama / ComfyUI 未触碰。
- userdata 工作流副本与真机库为运行时产物，未入库；规则表已归零。

## 5. 未做

- 规则候选勾选/驳回、差异预览、冲突人工裁决入口；规则管理界面为后续切片。
