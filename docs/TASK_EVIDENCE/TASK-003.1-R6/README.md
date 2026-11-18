# TASK-003.1-R6 证据目录

## 任务范围

M3「模型身份库与规则引擎」第一切片：**模型清单只读对接**。

从 ComfyUI `/object_info` 拉取在册模型文件名，按 Checkpoint / CLIP / VAE / LoRA 分组；当用户在设置中配置了本机外部模型目录时，对文件名做只读存在性核对（`on_disk`）；未配置目录时标记为未知（`null`），不臆测为不存在。本轮不复制、不哈希、不修改任何模型权重。

## 文件清单

| 文件 | 说明 |
| --- | --- |
| `execution-report.md` | 执行过程与改动说明 |
| `test-results.md` | 测试与构建结果明细 |
| `environment-report.md` | 运行环境与真机服务版本 |
| `git-diff.md` / `git-diff-raw.txt` | 代码差异说明与原始 diff |
| `known-issues.md` | 本轮未闭环项与遗留 backlog |
| `pytest-output.txt` | 后端 pytest 原始输出 |
| `frontend-build.txt` | 前端 `tsc -b && vite build` 原始输出 |
| `samples/catalog-summary.json` | 真机 `/api/models/catalog` 返回的四组清单快照 |
| `screenshots/` | 真机浏览器验收截图 |
| `logs/` | 运行日志（本轮无留存需要，暂空） |

## 边界声明

- 本轮只做只读清单拉取与本机文件存在性核对；**未实现** SHA256 身份库、架构/模型/Checkpoint 三级规则继承、规则来源/可信度/版本/回退、多模型规则组合与冲突检测、动态检索、云端研究资料导入审核（均属后续 M3 切片）。
- 未向 ComfyUI 提交出图任务；未对接 Ollama 对话生成（M4）；未对接 ComfyUI 队列/进度/结果/输出目录索引（M6）。
- 未改动 main 分支；所有改动落在 dev。
