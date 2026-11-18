# TASK-003.1-R17 证据目录

M3 第十二切片：工作流 checkpoint 规则上下文检索。

## 交付物

- `backend/rule_store.py`：`context_for_checkpoint()` 归集 checkpoint/架构/全局相关规则；`_checkpoint_architecture()` 关联底座标签（兼容架构事实已分流到架构级）。
- `backend/workflow_api.py`：`GET /api/workflows/{id}/rules`，从分析结果取 checkpoint 文件名，返回上下文规则；未识别/未登记返回 unregistered。
- `backend/test_workflow_rules.py`：3 例——注册上下文继承架构规则、未知 checkpoint 未登记、无 checkpoint 未识别。

## 切片边界

- 仅按 checkpoint 精确匹配；启用 LoRA 规则组合未纳入（暂无 LoRA 规则来源）。
- 上下文只归集规则，尚未装配为发给 LLM 的裁剪提示。

## 验收记录

| 项 | 结果 |
| --- | --- |
| 后端 pytest | 122 passed, 1 warning（见 `pytest-output.txt`） |
| 前端构建 | tsc -b && vite build exit 0（见 `frontend-build.txt`） |
| 真机闭环 | `samples/smoke-context.json`（14 checkpoint + 2 architecture/SDXL 1.0；ghost 未注册；清理归零） |
