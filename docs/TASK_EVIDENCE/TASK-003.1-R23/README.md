# TASK-003.1-R23 证据目录

M3 第十八切片：Resolution 解析保留括号内尺寸。

## 交付物

- `backend/value_normalize.py`：Resolution 在原始文本提取 `W×H`（含括号内），重复尺寸去重；数值/列表字段维持尾部备注剥离口径。
- `backend/test_value_normalize.py`：括号内尺寸提取、重复去重断言。

## 口径

- Resolution 尺寸常出现在括号备注内，提取基于原始 `raw`，不走 R21 的尾部剥离。
- 数值（Steps/CFG/Clip Skip）与列表（Sampler/Scheduler）仍先剥离尾部括号备注再解析。
- 无任何 `W×H` 的散文型 Resolution 保持 structured=None。

## 验收记录

| 项 | 结果 |
| --- | --- |
| 后端 pytest | 158 passed, 1 warning（见 `pytest-output.txt`） |
| 前端构建 | tsc -b && vite build exit 0（见 `frontend-build.txt`） |
| 真机闭环 | `samples/smoke-res-paren.json`（括号内三组尺寸结构化；Clip Skip 备注剥离；清理归零） |
