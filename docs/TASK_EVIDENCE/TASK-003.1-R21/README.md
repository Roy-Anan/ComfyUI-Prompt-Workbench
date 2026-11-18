# TASK-003.1-R21 证据目录

M3 第十六切片：参数值剥离尾部备注后再结构化解析。

## 交付物

- `backend/value_normalize.py`：尾部括号备注剥离；单值列表；`raw` 保留原值。
- `backend/test_value_normalize.py`：备注剥离、单值列表、两套建议不混并断言。
- `backend/test_rule_compare.py`：剥离备注后的调度器命中比对断言。

## 口径

- 只剥离**尾部**中文/英文括号备注（适用条件、示例说明）；清洗副本喂现有 normalizer，原值进 `raw`。
- Sampler/Scheduler 单值归单元素列表；分号分隔的两套建议不拆分、不混并。

## 验收记录

| 项 | 结果 |
| --- | --- |
| 后端 pytest | 151 passed, 1 warning（见 `pytest-output.txt`） |
| 前端构建 | tsc -b && vite build exit 0（见 `frontend-build.txt`） |
| 真机闭环 | `samples/smoke-notes.json`（Scheduler 结构化 list ["Karras"] 并 resolved；清理归零） |
