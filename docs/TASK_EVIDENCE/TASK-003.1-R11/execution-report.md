# R11 执行报告

## 目标

在 R10 只读检索之上，补齐规则的写入与删除 HTTP 接口，并纳入既有本地会话与 CSRF 保护。

## 实现

1. `backend/main.py`
   - `RuleUpsert`：level、scope_key、rule_key、value、provenance、confidence、version、note；键长/备注长度由 pydantic 限定。
   - `RuleDelete`：level、scope_key、rule_key。
   - `POST /api/rules`：调 `rule_store.upsert_rule`；`RuleError` 转 400；返回落库记录。
   - `DELETE /api/rules`：先校验层级合法，再 `delete_rule`，返回 `{removed: bool}`。
2. `frontend/src/api.ts`：`apiDelete(path, body)`，复用统一 request（自动带 CSRF 头）。

## 口径对齐

- 写/删为状态变更，cookie 会话由中间件校验 `X-Workbench-CSRF`；Bearer 测试调用豁免。
- 结构校验双重把关：pydantic 模型 + 引擎 `RuleRecord.validate()`；非法记录不入库。
- 删除按 level/scope_key/rule_key 精确匹配，不做模糊删除。

## 未纳入本轮

前端规则管理界面、旧 profiles 文本结构化导入、多模型/LoRA 规则组合、冲突人工裁决、动态检索、LLM 上下文组装、版本/差异回退。
