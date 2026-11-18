# R18 执行报告

## 目标

基于 R17 归集的上下文规则，装配成可下发给本地 LLM 的裁剪提示载荷：继承优先级由程序确定，字段保留来源与可信度；冲突与未知如实标注，模型不被要求猜测；只携带本上下文相关规则。

## 改动

### 后端

- `rule_prompt.py`（新增）
  - `build_prompt_context(context)`：注册上下文把 checkpoint/架构/全局规则转成引擎记录，调用 `resolve_context` 按三级继承解析；输出 `{status, checkpoint, architecture, fields, conflicts, unknown, instruction}`。
  - 字段条目：`resolved` 带 `source`（层级/作用域/来源/可信度/版本/备注）；`conflict` 带 `sources` 与说明；`unknown` 无值。未注册上下文返回空字段集与「不得依据模型名猜测」指令。
- `rule_engine.py`
  - `resolve_field` / `resolve_context` 增加可选 `architecture_scope`；checkpoint 上下文按显式架构家族作用域检索架构规则，避免把 checkpoint 文件名误当架构作用域。
- `workflow_api.py`
  - `GET /api/workflows/{workflow_id}/rules/prompt`：无识别 checkpoint 直接装配未注册载荷；有文件名先取 R17 上下文再装配。

## 过程修正

- 首跑架构/全局字段 `source_level=None`：引擎原实现把 checkpoint 作用域同时当作架构作用域检索，架构规则落在不同 scope_key 下被漏掉；增加 `architecture_scope` 显式传参后修正。
- `resolve_context` 返回的记录为引擎对象，键取属性访问而非下标。

## 真机过程

1. 启动后端，导入 IntoRealism 档案 16 条、0 拒绝。
2. 工作流 `suyuexisdxlapi.json` → `intorealismUltra_v80.safetensors`；提示载荷 16 字段（14 checkpoint + 2 architecture/SDXL 1.0），0 冲突；Steps=6~12，source=checkpoint，confidence=authoritative。
3. `ghost_missing.safetensors` 提示载荷 unregistered、0 字段。
4. 清理后规则表 0 条。

## 结论

切片目标达成；载荷继承口径与引擎一致，来源可审计，未登记/冲突/未知均不臆造。
