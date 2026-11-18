# TASK-003.1-R7 证据目录

## 任务范围

M3「模型身份库与规则引擎」第二切片：**模型身份库骨架与元数据缓存**。

在 R6 只读清单基础上，新增 SQLite 身份表，为已索引的本机权重记录绝对路径、文件大小、修改时间与可空 SHA256；目录索引刷新元数据，大小或 mtime 变化使缓存哈希失效；SHA256 流式计算、按需触发并缓存，大 checkpoint 不做 eager 哈希。清单接口给每条在册模型回挂身份摘要；前端清单展示大小与已校验/未哈希状态。本轮不复制、不修改模型权重；规则继承、冲突检测等仍属后续切片。

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
| `samples/identity-summary.json` | 真机身份摘要与按需哈希结果快照 |
| `screenshots/` | 真机浏览器验收截图 |
| `logs/` | 运行日志（本轮无留存需要，暂空） |

## 边界声明

- 本轮只落身份库骨架与元数据缓存；**未实现**架构/模型/Checkpoint 三级规则继承、规则来源/可信度/版本/回退、多模型与实际启用 LoRA 规则组合、冲突检测、动态检索、云端研究资料导入审核。
- 哈希为按需触发，尚无全量/定时哈希策略与前端触发入口；VAE/CLIP 目录本轮未进身份库索引。
- 未向 ComfyUI 提交出图任务；未对接 Ollama 对话生成（M4）；未对接 ComfyUI 队列/进度/结果/输出目录索引（M6）。
- 未改动 main 分支；所有改动落在 dev。
