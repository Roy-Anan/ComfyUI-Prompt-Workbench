# R16 执行报告

## 目标

让档案导入覆盖引擎的三级层级：架构相关事实归到架构级作用域，模型个体事实归到 checkpoint 级，避免把架构结论错挂到某一份 checkpoint 上。

## 实现

1. `backend/profile_parser.py`
   - 新增 `ARCHITECTURE_SECTIONS = {"ARCHITECTURE"}`。
   - `candidates_to_records`：ARCHITECTURE 节记录 `level="architecture"`、`scope_key=profile.architecture`；其余记录沿用传入的 checkpoint level 与 scope_key。底座标签缺失时架构记录 scope_key=None，交由导入层拒绝。
2. `backend/profile_source.py`
   - `import_profile` 不再强制 checkpoint 级，改为按记录自带 `level`/`scope_key` 调 `upsert_rule`。
   - 非 global 记录缺少 scope_key 时抛 `RuleError`，计入 `rejected`，不中断整批导入。

## 口径对齐

- 层级优先级仍由引擎程序确定：checkpoint > architecture > global；本轮只做装载分流，不改继承/冲突/未知判定。
- 不擅自归类：架构字段拿不到底座标签时拒绝并回报，不归 checkpoint、不提升 global。
- 作用域隔离：真机验证 checkpoint 上下文解析架构字段为 unknown，架构规则不泄漏进 checkpoint 作用域（与引擎既有 `test_checkpoint_rule_does_not_leak_into_architecture_context` 口径一致）。
- 不造全局规则：旧档案没有跨模型通用事实来源，global 级留待后续明确来源再装载。

## 未纳入本轮

global 级规则装载；架构标签归一化与同义归并；结构化参数前端展示与比对；逐候选勾选/驳回/差异预览；多模型/LoRA 组合；冲突人工裁决；动态检索；LLM 上下文装配；版本/差异回退。
