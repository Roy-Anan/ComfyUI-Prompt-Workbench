# R22 测试结果

## 后端单元 / 接口测试

- 命令：`.venv\Scripts\python.exe -m pytest -q`（backend 目录）
- 结果：**156 passed, 1 warning in 5.75s**
- `test_workflow_service.py` 新增：
  - `test_api_parser_extracts_latent_size`：API 样本 latent 节点 → `{node_id, width:832, height:1216}`；
  - `test_api_parser_without_latent_reports_none`：无 latent 节点时报告 `latent=None`。
- `test_workflow_rules.py`：compare 接口测试补 latent 节点，断言 actuals 含 `width=704`、`height=1024`。
- `test_rule_compare.py` 新增：
  - 实际尺寸在规则集合内 → match；
  - 不在集合内 → out_of_set；
  - 缺宽/高 → unknown，reason=`actual_missing`。
- 唯一 warning：StarletteDeprecationWarning（既有遗留，未改）。

## 前端构建

- 命令：`npm run build`（frontend 目录，`tsc -b && vite build`）
- 结果：exit 0；`index-IXKUmsZF.js 156.95 kB │ gzip 50.82 kB`，CSS 5.44 kB。

## 真机冒烟

见 `samples/smoke-resolution.json` 与 `execution-report.md`：

- 导入 IntoRealism 档案 17 条、0 拒绝。
- latent 704×1024 持久化并回读；actuals 注入宽高；Resolution 规则 {896×1152, 832×1216}，实际 704×1024 → out_of_set。
- 清理后规则表 0 条。

原始输出见 `pytest-output.txt`、`frontend-build.txt`。
