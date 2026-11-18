# R19 测试结果

## 后端单元 / 接口测试

- 命令：`.venv\Scripts\python.exe -m pytest -q`（backend 目录）
- 结果：**137 passed, 1 warning in 5.81s**
- 新增 `test_rule_compare.py`（8 passed）
  - range 命中 / 越界；floor 命中 / 越界；value 相等；列表集合大小写归一命中；非数值实际 unknown；未结构化规则 unknown；冲突规则直通 unknown；工作流级计数汇总。
- `test_workflow_rules.py` 补 2 例：注册工作流比对含实际参数与计数；无 checkpoint 工作流空比对集。
- 唯一 warning：StarletteDeprecationWarning（既有遗留，未改）。

## 前端构建

- 命令：`npm run build`（frontend 目录，`tsc -b && vite build`）
- 结果：exit 0；`index-IXKUmsZF.js 156.95 kB │ gzip 50.82 kB`，CSS 5.44 kB。

## 真机冒烟

见 `samples/smoke-compare.json` 与 `execution-report.md`：

- 导入 IntoRealism 档案：16 条，0 拒绝；重新导入 R5 API 样本。
- 实际参数：steps 35、cfg 5.5、sampler_name dpmpp_2m_sde、scheduler karras。
- 比对：Steps → out_of_range(6~12)；CFG → out_of_range(1.5~2)；Sampler → out_of_set；Scheduler 带备注未结构化 → unknown；其余非参数字段 unknown。
- 清理后规则表 0 条。

原始输出见 `pytest-output.txt`、`frontend-build.txt`。
