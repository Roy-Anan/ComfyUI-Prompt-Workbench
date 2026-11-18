# R10 执行报告

## 目标

在 R9 纯解析层之上落地规则持久化：规则进 SQLite，可按层级/作用域检索，并把存储规则交给引擎做三级继承解析。

## 实现

1. `backend/rule_store.py`
   - `workbench_rule` 表：`level, scope_key, rule_key` 唯一；`value_json` 存 JSON；provenance/confidence/version/note；created_at/updated_at。
   - `upsert_rule`：写入前 `RuleRecord.validate()`；同三元组冲突时替换值与元数据。
   - `lookup_rule` / `list_rules`（可按 level、scope_key 过滤）/ `delete_rule`。
   - `load_records` 装载为 `RuleRecord`；`resolve_stored` 调 `rule_engine.resolve_context`。
2. `backend/main.py`
   - `initialize_database` 调 `rule_store.ensure_schema`。
   - `GET /api/rules`：清单，可选 level/scope_key 过滤。
   - `GET /api/rules/resolve`：`level`、`scope_key`、`keys`（逗号分隔）；只解析请求键；非法层级 400、空键 400。
3. `backend/conftest.py`：把 `client` fixture 从 test_main 抽出共享。

## 口径对齐

- 写入前结构校验，非法记录不入库。
- 检索只返回请求键对应的解析结果；冲突与未知如实上报，不替选、不补默认。
- 数据库连接复用 `model_identity.connect`（同一 workbench.sqlite3）。

## 未纳入本轮

规则写入/导入 HTTP 接口、旧 profiles 文本结构化入库、前端规则管理界面、多模型/LoRA 组合、冲突人工裁决、动态检索、LLM 上下文组装、版本/差异回退。
