# TASK-003.1-R4 证据目录

## 任务范围

用用户提供的两份真实 ComfyUI UI 界面格式工作流样本，在真机上验证只读解析与外部服务对接；并补齐 UI 解析中模型 / LoRA 节点的只读参数提取。

1. 真机盘点 `D:\AI` 下的 Ollama 与 ComfyUI 整合包位置、模型目录、输出目录与运行状态。
2. 启动本机 Ollama（11434）与 ComfyUI（8188），经工作台 `/api/services/status` 探测均在线。
3. 两份样本导入工作台：识别正/负向 Prompt 节点、Checkpoint、LoRA 与强度，与 ComfyUI 真机 `object_info` 清单逐项核对。
4. 补后端只读提取：UI 节点 `widgets_values` 中的 checkpoint / lora 文件名与强度映射到报告 `inputs`；UI 工作流仍为只读，不开放写入。
5. 补 1 个回归用例；后端 63 passed，前端 `tsc -b && vite build` 通过。

## 文件清单

| 文件 | 说明 |
| --- | --- |
| `Doubao-Receipt.md` | 豆包本轮完整原始回执（不摘录、不润色） |
| `execution-report.md` | 执行过程与改动说明 |
| `test-results.md` | 测试与构建结果明细 |
| `environment-report.md` | 运行环境、本机服务与模型目录版本 |
| `git-diff.md` / `git-diff-raw.txt` | 代码差异说明与原始 diff |
| `known-issues.md` | 本轮未闭环项与遗留 backlog |
| `pytest-output.txt` | 后端 pytest 原始输出 |
| `frontend-build.txt` | 前端 `tsc -b && vite build` 原始输出 |
| `samples/` | 两份真实样本原始 JSON 副本 |
| `screenshots/` | 真机浏览器验收截图 |
| `logs/` | 运行日志（本轮无留存需要，暂空） |

## 边界声明

- 本轮改动后端 `workflow_service.py` 与 `test_workflow_service.py`；前端无代码改动。
- 两份样本均为 **UI 界面格式**（根含 `nodes` 数组与 `links`），按当前设计只做只读解析；白名单确认与 Prompt 写入仅对 API workflow 开放，本轮未在 UI 样本上尝试写入。
- Ollama 对话生成适配器、ComfyUI 任务提交 / 结果拉取 / 输出目录对接属于 M4 / M6 范围；本轮只做连通性探测与模型清单核对，未实现这些能力。
- 未改动 main 分支；所有改动落在 dev。
