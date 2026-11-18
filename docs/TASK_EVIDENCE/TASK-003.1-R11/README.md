# TASK-003.1-R11 证据目录

M3 第六切片：规则写入/删除接口与会话 CSRF 保护。

## 交付物

- `backend/main.py`：`POST /api/rules`（upsert）、`DELETE /api/rules`（删除）；`RuleUpsert`/`RuleDelete` 模型。
- `backend/test_rule_api.py`：upsert/删除/非法记录拒绝接口用例。
- `frontend/src/api.ts`：补齐 `apiDelete`。

## 切片边界

- 写/删走既有本地会话与 CSRF 中间件；非法记录 pydantic + 引擎双重校验，400 不写库。
- 无前端规则管理界面；旧 profiles 导入、规则组合、冲突裁决、动态检索、LLM 上下文组装留后续切片。

## 验收记录

| 项 | 结果 |
| --- | --- |
| 后端 pytest | 100 passed, 1 warning（见 `pytest-output.txt`） |
| 前端构建 | tsc -b && vite build exit 0（见 `frontend-build.txt`） |
| 真机写删闭环 | `samples/smoke-rules-write.json` |
