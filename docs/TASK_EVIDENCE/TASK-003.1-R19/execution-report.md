# R19 执行报告

## 目标

把规则库中已结构化的生成参数，与工作流采样器节点的实际参数做保守比对：能从两侧读出事实才给结论，读不出或不可比时归 unknown，不推断匹配或冲突。

## 改动

### 后端

- `workflow_service.py`
  - 新增 `_sampler_params(inputs)`：只复制 steps/cfg/sampler_name/scheduler/denoise 标量，链路数组与无关输入不进入。
  - API 与 UI 两条解析路径的采样器组都补 `params` 快照。
- `rule_compare.py`（新增）
  - `_FIELD_TO_ACTUAL`：规则字段后缀映射到采样器实际参数键。
  - `compare_rule(rule, actuals)`：resolved 且字段可比、规则已结构化才进入判定；数值走 range/floor/value，列表/分辨率走集合匹配；其余情形 unknown 并给 reason。
  - `compare_workflow(payload, actuals)`：逐字段比对，汇总 counts。
- `workflow_api.py`
  - `_sampler_actuals(report)`：取首个采样器组 params。
  - `GET /api/workflows/{workflow_id}/rules/compare`：未注册返回空比对集；注册先装配提示载荷再比对。

## 过程修正

- 首跑真机 params 为空：现存工作流副本是改动前导入的缓存报告，重开不重新解析；重新导入 R5 样本后 params 正常提取（steps 35、cfg 5.5、sampler_name dpmpp_2m_sde、scheduler karras）。
- 比对顺序：先判规则状态（conflict/unknown 直通），再判字段是否可比，再判规则是否结构化，最后才进入数值/集合判定。

## 真机过程

1. 启动后端，导入 IntoRealism 档案 16 条、0 拒绝；重新导入 R5 API 样本。
2. 比对结果：Steps 35 对规则 6~12 → out_of_range；CFG 5.5 对 1.5~2 → out_of_range；Sampler dpmpp_2m_sde 对 [Euler A Karras, Exponential] → out_of_set；Scheduler `Karras（Euler A 时）` 带备注未结构化 → unknown；其余非参数字段 unknown。
3. 清理后规则表 0 条。

## 结论

比对层口径保守：真实参数与档案建议的差异被如实标出，无法判定的字段不补结论；只读，不回写工作流。
