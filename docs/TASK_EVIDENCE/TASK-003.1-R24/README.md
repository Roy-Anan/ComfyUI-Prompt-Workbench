# TASK-003.1-R24 证据目录

M3 第十九切片：Clip Skip 实际参数链路（CLIPSetLastLayer）。

## 交付物

- `backend/workflow_service.py`：识别 CLIPSetLastLayer，读取 `stop_at_clip_layer`，派生正数 `clip_skip`（API/UI 两段）。
- `backend/workflow_api.py`：actuals 注入派生 `clip_skip`。
- `backend/rule_compare.py`：数值比对区分缺值（actual_missing）与非数值（actual_not_numeric）。
- 测试：`test_workflow_service.py`、`test_workflow_rules.py`、`test_rule_compare.py`。

## 口径

- ComfyUI `stop_at_clip_layer` 取值域 -24…-1（负停止层数）；规则层比较正数跳过层数，`clip_skip = -stop_at_clip_layer`。
- 非负、非整数或缺节点不换算，报告 `clip_skip=None`，比对归 unknown。
- 符号换算基于节点固定取值域，不做层数等价猜测。

## 验收记录

| 项 | 结果 |
| --- | --- |
| 后端 pytest | 163 passed, 1 warning（见 `pytest-output.txt`） |
| 前端构建 | tsc -b && vite build exit 0（见 `frontend-build.txt`） |
| 真机闭环 | `samples/smoke-clip-skip.json`（规则 2 与实际 -2 派生 2 判 match；清理归零） |
