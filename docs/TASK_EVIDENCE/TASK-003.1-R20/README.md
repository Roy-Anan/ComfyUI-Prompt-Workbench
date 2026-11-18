# TASK-003.1-R20 证据目录

M3 第十五切片：架构标签归一化与同家族规则归并。

## 交付物

- `backend/architecture_normalize.py`（新增）：标签 → 规范家族纯函数层。
- `backend/rule_store.py`：上下文按规范家族归并架构规则；未登记模型不回退其他模型标签；返回 `architecture_family`/`architecture_label`。
- `backend/profile_parser.py`：导入时补 checkpoint 桶 `IDENTITY::Base Architecture` 身份指针。
- `backend/rule_prompt.py`：提示载荷透传家族与原始标签。
- `backend/workflow_api.py`：未登记占位补家族/标签字段。
- `backend/test_architecture_normalize.py`：8 例归一化单测。
- `backend/test_rule_store.py`：同家族归并、混合标签隔离、未登记不带家族断言。
- `backend/test_profile_source.py`：身份指针落库断言同步更新。

## 归一化口径

- 规范家族：`SD1.5`、`SDXL`、`Pony`；未识别留 `other`。
- 同义变体（`SDXL`/`SDXL 1.0`/`sdxl`）归同一家族；混合/派生标签标 `mixed`，不并入纯家族。
- 两侧都识别才按家族严格匹配；仅一侧识别或都未识别时不做子串猜测。

## 验收记录

| 项 | 结果 |
| --- | --- |
| 后端 pytest | 147 passed, 1 warning（见 `pytest-output.txt`） |
| 前端构建 | tsc -b && vite build exit 0（见 `frontend-build.txt`） |
| 真机闭环 | `samples/smoke-normalize.json`（SDXL 1.0 纳入 SDXL + SDXL 1.0，排除混合标签；清理归零） |
