# R14 执行报告

## 目标

在 R13 只读预览之上，打通「档案候选 → 规则库」的审核导入链路：把一份旧档案的候选落为 checkpoint 级规则，落库前经引擎结构校验，非法候选不阻断整批。

## 实现

1. `backend/profile_source.py`
   - `import_profile(connection, file_name, source_dir=None)`：复用 `preview_profile` 取候选；无完整 checkpoint 文件名抛 `RuleError`；逐条 `rule_store.upsert_rule(level="checkpoint", scope_key=filename, ...)`；`RuleError` 捕获进 `rejected`；返回 `{file, filename, imported, rejected, unknown_fields}`。
2. `backend/main.py`
   - `ProfileImport.file_name`（1–120 字符）。
   - `POST /api/profiles/import`：打开本地 SQLite，`ensure_schema` 后导入；`FileNotFoundError` → 404；`RuleError` → 400。写操作走既有本地会话与 CSRF 中间件。

## 口径对齐

- 校验双重把关：候选投影字段经引擎 `RuleRecord.validate()`（层级/作用域/来源/可信度枚举）；不合法记录不入库。
- 作用域精确：checkpoint 规则 scope_key 为档案完整 checkpoint 文件名，与旧 `profile_lookup.py` 精确匹配口径一致，不做模糊推断。
- 不造默认：未知字段不产候选；导入报告原样回报 `unknown_fields`。
- 不调外部服务：导入为本地 SQLite 写入，不触达 ComfyUI/Ollama。

## 未纳入本轮

architecture/global 级规则装载、参数结构化拆分、逐候选勾选/驳回/差异预览、前端导入与审核界面、多模型/LoRA 组合、冲突人工裁决、动态检索、LLM 上下文装配、版本/差异回退。
