# R9 执行报告

## 目标

M3 第四切片：在身份库之后落地规则引擎骨架。规则记录结构化，继承优先级由程序确定；冲突与未知信息不由 LLM 猜测。

## 实现

1. `backend/rule_engine.py`
   - `LEVEL_ORDER = ("checkpoint", "architecture", "global")`，由具体到一般。
   - `RuleRecord`：level / scope_key / key / value / provenance / confidence / version / note，`validate()` 校验层级、键、作用域、来源、可信度。
   - `resolve_field`：checkpoint → architecture → global 逐级查找，首个覆盖层级胜出；同层值不一致返回 `conflict`；无覆盖返回 `unknown`。
   - `resolve_context`：批量解析请求键，汇总 `conflicts` / `unknown`；只解析请求键，不外送无关规则。
   - `summarize_rules`：按层级/作用域盘点规则数量与键。
2. `backend/test_rule_engine.py`：8 例，覆盖三级优先级、回落 global、不跨上下文泄漏、同层冲突、未知不造默认、上下文汇总、记录校验、盘点。

## 口径对齐

- 继承优先级程序确定，不交给模型推断。
- 同层冲突只标记、不替选；未覆盖字段标 unknown，不补默认值。
- 每条解析结果回挂来源层级、作用域、provenance、confidence、version、note，便于后续审计。

## 未纳入本轮

规则持久化存储、旧 profiles 文本结构化导入、多模型与启用 LoRA 规则组合、冲突人工裁决界面、动态检索、LLM 上下文组装。
