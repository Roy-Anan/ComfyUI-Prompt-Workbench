# TASK-003.1-R25 证据目录

M3 第二十切片：多采样器组 actuals 保守标注。

## 交付物

- `backend/workflow_api.py`：`_sampler_actuals` 遍历全部采样器组，新增 `sampler_group_count` 与 `sampler_groups`（每组 node_id + params 摘要）；顶层 actuals 仍取首个有参数的组。
- 测试：`test_workflow_rules.py` 双采样器组样本断言。

## 口径

- 多组参数不合并、不替选；比对判定仅对应首组。
- 逐组独立比对、组间冲突提示为后续切片。

## 验收记录

| 项 | 结果 |
| --- | --- |
| 后端 pytest | 164 passed, 1 warning（见 `pytest-output.txt`） |
| 前端构建 | tsc -b && vite build exit 0（见 `frontend-build.txt`） |
| 真机闭环 | `samples/smoke-multi-groups.json`（count=2，首组 25/7.0，次组 30/6.0；清理归零） |
