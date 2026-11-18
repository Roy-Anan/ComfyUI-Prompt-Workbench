# R23 测试结果

## 后端单元 / 接口测试

- 命令：`.venv\Scripts\python.exe -m pytest -q`（backend 目录）
- 结果：**158 passed, 1 warning in 5.81s**
- `test_value_normalize.py` 新增：
  - `test_resolution_keeps_sizes_inside_parenthetical`：括号内三组尺寸 → resolutions；
  - `test_resolution_de_duplicates_repeated_sizes`：重复尺寸去重为单元素。
- 既有断言保持：数值/列表字段尾部备注剥离；散文型 Resolution → None。
- 唯一 warning：StarletteDeprecationWarning（既有遗留，未改）。

## 前端构建

- 命令：`npm run build`（frontend 目录，`tsc -b && vite build`）
- 结果：exit 0；`index-IXKUmsZF.js 156.95 kB │ gzip 50.82 kB`，CSS 5.44 kB。

## 真机冒烟

见 `samples/smoke-res-paren.json` 与 `execution-report.md`：

- 导入 HuslyoRealismSDXL_v3 档案 20 条、0 拒绝。
- Resolution 括号内三组尺寸结构化；Clip Skip `2（非 V3 独立参数）`→value 2；Steps `30~32`→range；Scheduler `Karras`→list。
- 清理后规则表 0 条。

原始输出见 `pytest-output.txt`、`frontend-build.txt`。
