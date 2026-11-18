# TASK-003.1-R18 证据目录

M3 第十三切片：上下文规则装配为 LLM 裁剪提示。

## 交付物

- `backend/rule_prompt.py`：`build_prompt_context()` 纯函数层，把 R17 上下文经引擎继承解析为提示载荷。
- `backend/rule_engine.py`：`resolve_field`/`resolve_context` 增加可选 `architecture_scope`，显式区分 checkpoint 与架构家族作用域。
- `backend/workflow_api.py`：`GET /api/workflows/{id}/rules/prompt`。
- `backend/test_rule_prompt.py`：3 例（继承与来源保留、同层冲突、未注册空载荷）。
- `backend/test_workflow_rules.py`：补 2 例接口层提示载荷断言。

## 切片边界

- 只装配载荷；不调用 Ollama、不发送提示、不回写工作流。
- LoRA 规则组合、冲突人工裁决界面、裁剪长度控制、动态检索未实现。

## 验收记录

| 项 | 结果 |
| --- | --- |
| 后端 pytest | 127 passed, 1 warning（见 `pytest-output.txt`） |
| 前端构建 | tsc -b && vite build exit 0（见 `frontend-build.txt`） |
| 真机闭环 | `samples/smoke-prompt.json`（16 字段：14 checkpoint + 2 architecture/SDXL 1.0；ghost 未注册；清理归零） |
