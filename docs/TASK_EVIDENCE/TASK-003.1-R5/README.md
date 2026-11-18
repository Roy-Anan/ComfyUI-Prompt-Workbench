# TASK-003.1-R5 证据目录

## 任务范围

用用户从 ComfyUI 导出的真实 **API 格式**工作流 `suyuexisdxlapi.json`，在真机跑通工作台缺的写入闭环：

导入 → 识别正/负向 Prompt 与模型/LoRA → 白名单确认 → 编辑工作副本 → 写入并完整性校验 → 刷新重开持久化 → 原始文件未改、版本快照保存写入前版本。

## 文件清单

| 文件 | 说明 |
| --- | --- |
| `Doubao-Receipt.md` | 豆包本轮完整原始回执（不摘录、不润色） |
| `execution-report.md` | 执行过程与改动说明 |
| `test-results.md` | 测试与构建结果明细 |
| `environment-report.md` | 运行环境与真机服务版本 |
| `git-diff.md` / `git-diff-raw.txt` | 代码差异说明与原始 diff |
| `known-issues.md` | 本轮未闭环项与遗留 backlog |
| `pytest-output.txt` | 后端 pytest 原始输出 |
| `frontend-build.txt` | 前端 `tsc -b && vite build` 原始输出 |
| `samples/` | 真实 API 格式样本原始 JSON |
| `screenshots/` | 真机浏览器验收截图 |
| `logs/` | 运行日志（本轮无留存需要，暂空） |

## 边界声明

- 本轮代码改动仅在 `backend/test_workflow_service.py` 补 1 条真实样本闭环回归用例；服务端解析/写入逻辑无改动，前端无代码改动。
- 闭环只在工作台内编辑工作副本 Prompt；**未向 ComfyUI 提交出图任务**，未拉取生成结果，未对接输出目录。
- Ollama 对话生成、ComfyUI 任务提交/进度/结果拉取仍属 M4 / M6 范围，本轮未实现。
- 未改动 main 分支；所有改动落在 dev。
