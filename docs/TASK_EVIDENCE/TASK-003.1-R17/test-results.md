# R17 测试结果

## 后端单元 / 接口测试

- 命令：`.venv\Scripts\python.exe -m pytest -q`（backend 目录）
- 结果：**122 passed, 1 warning in 5.52s**
- 新增测试文件：`test_workflow_rules.py`（3 passed）
  - `test_workflow_rules_context_matches_checkpoint_and_inherits`：注册 checkpoint、架构=SD1.5、三类规则键齐全，无关 checkpoint 规则不外泄。
  - `test_workflow_rules_unregistered_for_unknown_checkpoint`：未登记 checkpoint 返回 unregistered、空 checkpoint 规则。
  - `test_workflow_rules_unregistered_without_checkpoint`：无识别 checkpoint 返回 unregistered、reason=no_checkpoint_recognized。
- 唯一 warning：StarletteDeprecationWarning（既有遗留，未改）。

## 前端构建

- 命令：`npm run build`（frontend 目录，`tsc -b && vite build`）
- 结果：exit 0；`dist/assets/index-IXKUmsZF.js 156.95 kB │ gzip 50.82 kB`，CSS 5.44 kB。

## 真机冒烟

见 `samples/smoke-context.json` 与 `execution-report.md`：

- 导入 IntoRealism 档案：16 条，0 拒绝。
- 工作流 `suyuexisdxlapi.json` → checkpoint `intorealismUltra_v80.safetensors`；上下文 14 checkpoint + 2 architecture(SDXL 1.0) + 0 global。
- 临时工作流 `ghost_missing.safetensors` → unregistered。
- 清理后规则表 0 条。

原始输出见 `pytest-output.txt`、`frontend-build.txt`。
