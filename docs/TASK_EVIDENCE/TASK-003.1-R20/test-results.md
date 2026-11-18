# R20 测试结果

## 后端单元 / 接口测试

- 命令：`.venv\Scripts\python.exe -m pytest -q`（backend 目录）
- 结果：**147 passed, 1 warning in 5.79s**
- 新增 `test_architecture_normalize.py`（8 passed）
  - SDXL 变体同家族；SD1.5 与 SDXL 区分；Pony 独立；混合 Pony/SDXL 标 mixed；Illustrious 派生标 mixed；未识别留 other；空标签未匹配；两侧都匹配才判同家族。
- `test_rule_store.py` 补 2 例：同家族变体规则归并；混合标签隔离纯家族。
- `test_workflow_rules.py`：未登记上下文 `architecture`/`family` 为 None。
- `test_profile_source.py`：身份指针落库断言（imported 3、checkpoint 桶含 `IDENTITY::Base Architecture`）。
- 唯一 warning：StarletteDeprecationWarning（既有遗留，未改）。

## 前端构建

- 命令：`npm run build`（frontend 目录，`tsc -b && vite build`）
- 结果：exit 0；`index-IXKUmsZF.js 156.95 kB │ gzip 50.82 kB`，CSS 5.44 kB。

## 真机冒烟

见 `samples/smoke-normalize.json` 与 `execution-report.md`：

- 导入 huslyorealismxl（SDXL）、intorealismUltra（SDXL 1.0）、ponyDiffusionV6XL（Pony / SDXL 系），0 拒绝。
- intorealismUltra 上下文：family=SDXL，label=SDXL 1.0；架构 scope = `SDXL`、`SDXL 1.0`；混合标签未纳入；提示 17 字段。
- 清理后规则表 0 条。

原始输出见 `pytest-output.txt`、`frontend-build.txt`。
