# TASK-003.1-R22 证据目录

M3 第十七切片：Resolution 规则对接实际 latent 尺寸比对。

## 交付物

- `backend/workflow_service.py`：识别 LatentImage 节点，提取 width/height 写入报告 `latent`（API/UI 两段）。
- `backend/workflow_api.py`：`_sampler_actuals` 合并 latent 宽高到比对 actuals。
- `backend/rule_compare.py`：Resolution 规则 resolutions 与实际 (宽,高) 整数集合保守匹配。
- 测试：`test_workflow_service.py`、`test_workflow_rules.py`、`test_rule_compare.py`。

## 口径

- 规则 `resolutions.items=[{width,height}]`；实际 latent 宽高均为有效整数时才判定；集合内 match，否则 out_of_set。
- 缺宽/高、非数值归 `unknown`（reason=`actual_missing`）；散文型 Resolution 无结构化时保持 `rule_not_structured`。

## 验收记录

| 项 | 结果 |
| --- | --- |
| 后端 pytest | 156 passed, 1 warning（见 `pytest-output.txt`） |
| 前端构建 | tsc -b && vite build exit 0（见 `frontend-build.txt`） |
| 真机闭环 | `samples/smoke-resolution.json`（latent 704×1024；Resolution out_of_set；清理归零） |
