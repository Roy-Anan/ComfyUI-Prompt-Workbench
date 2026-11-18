# R25 测试结果

## 后端

- 命令：`.venv\Scripts\python.exe -m pytest -q`（backend）
- 结果：**164 passed, 1 warning in 5.87s**

新增断言：

- `test_workflow_rule_compare_lists_multiple_sampler_groups`：双组样本，`sampler_group_count=2`，顶层 `steps=20`，`sampler_groups` steps 序列 `[20, 30]`。

唯一 warning：StarletteDeprecationWarning（既有遗留，未改）。

## 前端

- 命令：`npm run build`（tsc -b && vite build）
- 结果：exit 0；构建产物大小与 R24 持平。

## 真机

见 `samples/smoke-multi-groups.json` 与 `execution-report.md`。
