# R18 测试结果

## 后端单元 / 接口测试

- 命令：`.venv\Scripts\python.exe -m pytest -q`（backend 目录）
- 结果：**127 passed, 1 warning in 5.52s**
- 新增 `test_rule_prompt.py`（3 passed）
  - 继承与来源保留：Steps 由 checkpoint 覆盖，架构/全局字段各自标注来源层级，来源可信度保留。
  - 同层冲突：CFG 两条同层异值 → `conflict`、值为 None、双来源，入 conflicts。
  - 未注册：空字段集，指令要求不得猜测。
- `test_workflow_rules.py` 补 2 例：注册工作流提示载荷含全局来源字段与继承指令；无 checkpoint 工作流返回未注册空载荷。
- 唯一 warning：StarletteDeprecationWarning（既有遗留，未改）。

## 前端构建

- 命令：`npm run build`（frontend 目录，`tsc -b && vite build`）
- 结果：exit 0；`index-IXKUmsZF.js 156.95 kB │ gzip 50.82 kB`，CSS 5.44 kB。

## 真机冒烟

见 `samples/smoke-prompt.json` 与 `execution-report.md`：

- 导入 IntoRealism 档案：16 条，0 拒绝。
- `suyuexisdxlapi.json` 提示载荷：16 字段（14 checkpoint + 2 architecture/SDXL 1.0），conflicts=[]、unknown=[]；Steps=6~12，source=checkpoint，confidence=authoritative。
- `ghost_missing.safetensors` → unregistered，0 字段。
- 清理后规则表 0 条。

原始输出见 `pytest-output.txt`、`frontend-build.txt`。
