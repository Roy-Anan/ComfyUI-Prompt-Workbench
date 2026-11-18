# R9 测试结果

## 后端 pytest

命令：`python -m pytest -q`（`.venv` Python 3.13.18，pytest 8.4.2）

结果：**88 passed, 1 warning in 4.26s**。原始输出见 `pytest-output.txt`。

### 新增用例（test_rule_engine.py，8 passed）

| 用例 | 覆盖点 |
| --- | --- |
| test_checkpoint_rule_overrides_architecture_and_global | checkpoint 覆盖 architecture/global |
| test_architecture_falls_back_to_global | architecture 命中；缺失回落 global |
| test_uncovered_field_is_unknown_not_defaulted | 无覆盖字段 unknown，不造默认 |
| test_same_level_conflict_is_marked_not_picked | 同层两值冲突，conflict + 双来源 |
| test_checkpoint_rule_does_not_leak_into_architecture_context | checkpoint 规则不进入 architecture 上下文 |
| test_resolve_context_reports_conflicts_and_unknowns | 批量解析汇总冲突/未知 |
| test_record_validates_level_and_provenance | 非法层级/作用域/来源拒绝 |
| test_summarize_rules_by_level | 按层级盘点 |

## 前端构建

命令：`npm run build`（Node v22.23.2，Vite 5.4.21）

结果：exit 0，33 模块，`dist/assets/index-IXKUmsZF.js 156.95 kB`。原始输出见 `frontend-build.txt`。本轮无前端代码改动。

## 真机核对

本轮为纯函数解析层，无新接口、无页面、不触碰 ComfyUI/Ollama；未做浏览器真机验收。解析快照见 `samples/rule-resolution.json`。
