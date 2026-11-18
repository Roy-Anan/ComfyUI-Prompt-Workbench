# R24 测试结果

## 后端

- 命令：`.venv\Scripts\python.exe -m pytest -q`（backend）
- 结果：**163 passed, 1 warning in 5.87s**

新增 / 调整断言：

- `test_api_parser_extracts_clip_skip_from_last_layer_node`：-2 → clip_skip 2。
- `test_api_parser_clip_skip_none_without_node`：无节点 → None。
- `test_api_parser_clip_skip_ignores_non_negative_stop_layer`：stop=0 → None。
- `test_clip_skip_value_match_and_mismatch`：actual 2 match；actual 1 out_of_range。
- `test_clip_skip_unknown_when_missing`：缺 actual → unknown / actual_missing。
- `test_workflow_rules.py`：接口样本加 CLIPSetLastLayer -2，断言 actuals `clip_skip==2`。

唯一 warning：StarletteDeprecationWarning（既有遗留，未改）。

## 前端

- 命令：`npm run build`（tsc -b && vite build）
- 结果：exit 0；`index-IXKUmsZF.js 156.95 kB │ gzip 50.82 kB`，CSS 5.44 kB。

## 真机

见 `samples/smoke-clip-skip.json` 与 `execution-report.md`。
