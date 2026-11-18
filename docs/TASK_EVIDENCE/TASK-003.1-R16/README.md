# TASK-003.1-R16 证据目录

M3 第十一切片：架构级规则随档案导入（分节分流）。

## 交付物

- `backend/profile_parser.py`：`candidates_to_records` 按分节分流；ARCHITECTURE 节→architecture 级（scope=底座标签），其余→checkpoint 级。
- `backend/profile_source.py`：导入按记录自带 level/scope 落库；无作用域的非 global 记录记 rejected。
- `backend/test_profile_parser.py`：形状断言更新为层级分流。
- `backend/test_profile_source.py`：架构级落库断言；无底座标签架构字段拒绝用例。

## 切片边界

- global 级规则本轮不装载：旧档案暂无跨模型通用事实来源。
- 架构标签为散文标签，未做归一化/同义归并；前端展示与跨模型继承在上下文装配切片再验。

## 验收记录

| 项 | 结果 |
| --- | --- |
| 后端 pytest | 119 passed, 1 warning（见 `pytest-output.txt`） |
| 前端构建 | tsc -b && vite build exit 0（见 `frontend-build.txt`） |
| 真机闭环 | `samples/smoke-levels.json`（11 条：9 checkpoint + 2 architecture/SD1.5，清理归零） |
