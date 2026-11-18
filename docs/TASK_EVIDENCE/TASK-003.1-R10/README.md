# TASK-003.1-R10 证据目录

M3 第五切片：规则 SQLite 持久化与检索接口骨架。

## 交付物

- `backend/rule_store.py`：规则表、upsert/查/删、JSON 值往返、装载为引擎记录、存储规则解析。
- `backend/test_rule_store.py`：7 个存储单元用例。
- `backend/test_rule_api.py`：3 个接口用例。
- `backend/conftest.py`：跨文件复用的 `client` fixture。
- `backend/main.py`：规则表初始化；`GET /api/rules`、`GET /api/rules/resolve`。

## 切片边界

- 本轮只做持久化与只读检索；规则写入/导入接口、旧 profiles 文本结构化入库、前端规则管理界面未实现。
- 不调 Ollama/ComfyUI；规则组合、冲突裁决、动态检索、LLM 上下文组装留后续切片。

## 验收记录

| 项 | 结果 |
| --- | --- |
| 后端 pytest | 98 passed, 1 warning（见 `pytest-output.txt`） |
| 前端构建 | tsc -b && vite build exit 0（见 `frontend-build.txt`） |
| 真机冒烟 | `samples/smoke-rules.json` |
