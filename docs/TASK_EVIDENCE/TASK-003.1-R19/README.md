# TASK-003.1-R19 证据目录

M3 第十四切片：结构化规则值与工作流实际参数保守比对。

## 交付物

- `backend/workflow_service.py`：采样器组补充 `params` 快照（steps/cfg/sampler_name/scheduler/denoise）。
- `backend/rule_compare.py`（新增）：`compare_rule()`/`compare_workflow()` 纯函数保守比对层。
- `backend/workflow_api.py`：`GET /api/workflows/{id}/rules/compare`。
- `backend/test_rule_compare.py`：8 例纯函数比对测试。
- `backend/test_workflow_rules.py`：补 2 例接口层比对断言。

## 比对口径

- 数值：range 区间内 / floor 下限 / value 相等；越界 `out_of_range`。
- 列表/分辨率：实际值归一后在集合内；不在 `out_of_set`。
- 不可判定：实际非数值、规则未结构化、字段不可比、规则冲突/未知 → `unknown`，不臆造。

## 验收记录

| 项 | 结果 |
| --- | --- |
| 后端 pytest | 137 passed, 1 warning（见 `pytest-output.txt`） |
| 前端构建 | tsc -b && vite build exit 0（见 `frontend-build.txt`） |
| 真机闭环 | `samples/smoke-compare.json`（Steps/CFG 越界、Sampler 不在集合；Scheduler 未结构化 unknown；清理归零） |
