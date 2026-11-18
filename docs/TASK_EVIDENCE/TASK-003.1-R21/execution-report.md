# R21 执行报告

## 目标

R15/R19 遗留：带备注的参数值（如 `Karras（Euler A 时）`、`25（使用指南参考，非强制固定值）`）此前整段回退原文、structured=None，比对归 unknown。本切片在结构化解析前剥离尾部括号备注，使核心值可被既有 normalizer 解析，同时保留原值可追溯。

## 改动

### 后端

- `value_normalize.py`
  - 新增 `_strip_trailing_parenthetical()`：循环剥离尾部 `（…）`/`(...)` 备注与尾随分隔符；括号在值内部、分号第二套建议不动。
  - `normalize()`：以清洗副本喂 normalizer，`raw` 保留原始文本。
  - `normalize_list()`：单个干净 token 也产出单元素列表（Sampler/Scheduler 单值合法）。
- 测试：备注剥离后数值/调度器解析、单值列表、分号两套建议留 None；比对层调度器命中。

## 过程核对

- 旧档案带备注样本：`Scheduler: Karras（Euler A 时）`、`Steps: 25（使用指南参考，非强制固定值）`、`CFG: 12（示例图参数…）`。
- 保守边界：`35；25~40` 这类示例/指南两套并存，本轮不拆分，structured=None，避免把两套建议混并成一个范围。

## 真机过程

1. 启动后端，导入 IntoRealism 档案 17 条、0 拒绝。
2. 规则库核对：Steps `6~12` range；CFG `1.5~2` range；Sampler list 两项；Scheduler `Karras（Euler A 时）` 剥离后 list ["Karras"]。
3. 重新导入 R5 API 样本，提示载荷中 Scheduler resolved、structured=list ["Karras"]；Steps/CFG 保持结构化。
4. 清理后规则表 0 条。

## 结论

尾部备注不再阻断结构化；核心值可参与 R19 保守比对；原值与备注仍随记录保留，两套建议未被臆造合并。
