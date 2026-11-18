# R21 测试结果

## 后端单元 / 接口测试

- 命令：`.venv\Scripts\python.exe -m pytest -q`（backend 目录）
- 结果：**151 passed, 1 warning in 5.88s**
- `test_value_normalize.py` 新增：
  - `25（使用指南参考，非强制固定值）`→value 25，raw 保留原值；
  - `12（示例图参数…）`→value 12；
  - `Karras（Euler A 时）`→list ["Karras"]，raw 保留原值；
  - `LCM`→单元素 list；
  - `35；25~40`→structured=None（两套建议不混并）。
- `test_rule_compare.py` 新增：剥离备注后的 Scheduler 规则与实际 `karras` 命中 match。
- 唯一 warning：StarletteDeprecationWarning（既有遗留，未改）。

## 前端构建

- 命令：`npm run build`（frontend 目录，`tsc -b && vite build`）
- 结果：exit 0；`index-IXKUmsZF.js 156.95 kB │ gzip 50.82 kB`，CSS 5.44 kB。

## 真机冒烟

见 `samples/smoke-notes.json` 与 `execution-report.md`：

- 导入 IntoRealism 档案 17 条、0 拒绝。
- Scheduler `Karras（Euler A 时）`→list ["Karras"]，提示载荷 resolved；Steps/CFG/Sampler 保持结构化。
- 清理后规则表 0 条。

原始输出见 `pytest-output.txt`、`frontend-build.txt`。
