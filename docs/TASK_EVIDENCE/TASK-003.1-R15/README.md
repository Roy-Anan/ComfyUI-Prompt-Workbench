# TASK-003.1-R15 证据目录

M3 第十切片：生成参数值结构化解析。

## 交付物

- `backend/value_normalize.py`：纯函数归一化层，数值/范围/下限/分辨率列表/枚举列表；解析失败 `structured=None`。
- `backend/profile_parser.py`：候选投影记录附 `structured`。
- `backend/rule_store.py`：新增 `structured_json` 列（旧库补列迁移），`value_json` 保持原始裸值。
- `backend/profile_source.py`：导入时透传 `structured`。
- `backend/test_value_normalize.py`：6 例覆盖数值/范围/下限/分辨率/列表/失败回退/候选记录。

## 切片边界

- 仅覆盖 Steps、CFG、Clip Skip、Resolution、Sampler、Scheduler 六类生成参数。
- 结构化结果尚未接前端展示或参数比对/冲突检测；散文/提示词/架构字段不拆。

## 验收记录

| 项 | 结果 |
| --- | --- |
| 后端 pytest | 118 passed, 1 warning（见 `pytest-output.txt`） |
| 前端构建 | tsc -b && vite build exit 0（见 `frontend-build.txt`） |
| 真机闭环 | `samples/smoke-structured.json`（16 条入库，四类参数结构化回读，清理归零） |
