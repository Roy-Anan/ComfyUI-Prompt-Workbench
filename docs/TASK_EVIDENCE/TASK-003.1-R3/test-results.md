# 测试结果 — TASK-003.1-R3

## 后端 pytest

- 命令：`.venv\Scripts\python.exe -m pytest -q`（`backend/`）
- 结果：**62 passed, 1 warning in 6.95s**，exit 0
- 警告：`StarletteDeprecationWarning`（httpx + starlette.testclient 弃用提示，既有遗留，非本轮引入）
- 原始输出：`pytest-output.txt`

## 前端构建

- 命令：`npm run build`（`frontend/`，内含 `tsc -b && vite build`）
- 结果：**exit 0**，33 modules transformed，Vite 5.4.21
- 原始输出：`frontend-build.txt`

## 用例覆盖对照

| 验收项 | 状态 | 证据 |
| --- | --- | --- |
| 既有 57 个后端用例回归 | 通过 | pytest 全绿 |
| `nodes` 字典兼容结构识别 | 通过 | `test_detect_api_workflow_wrapped_in_nodes` |
| 中转 conditioning 追溯 | 通过 | `test_passthrough_conditioning_node_trace_continues_upstream` |
| 版本快照存旧文本 | 通过 | `test_version_snapshot_keeps_previous_prompt_text` |
| 重开/重建 Store 持久化 | 通过 | `test_reimport_and_reopen_persists_across_store_instances` |
| 非白名单值变更拒绝 | 通过 | `test_structural_diff_rejects_non_whitelist_value_change` |
| 前端类型检查与打包 | 通过 | frontend-build.txt |
| 真机浏览器闭环 | 未执行 | 缺真实 API workflow 样本，见 known-issues |
| 真实出图端到端 | 未完成 | 不在本轮边界 |
