# TASK-003.1-R3 证据目录

## 任务范围

在 R2（服务端测试 57 passed）基础上，不依赖真实 ComfyUI 样本，完成工作流服务的安全与追溯收尾：

1. 补齐三类回归测试：`nodes` 字典兼容结构识别、版本快照保存旧文本断言、重复导入/重开持久化断言。
2. 修复中转 conditioning 节点（ConditioningCombine / ConditioningZeroOut 等）向上追溯断裂的问题。
3. 将写入前/后的整对象 `!=` 比对替换为结构化白名单 diff，逐节点逐字段校验。

## 文件清单

| 文件 | 说明 |
| --- | --- |
| `Doubao-Receipt.md` | 豆包本轮完整原始回执（不摘录、不润色） |
| `execution-report.md` | 执行过程与改动说明 |
| `test-results.md` | 测试与构建结果明细 |
| `environment-report.md` | 运行环境版本 |
| `git-diff.md` / `git-diff-raw.txt` | 代码差异说明与原始 diff |
| `known-issues.md` | 本轮未闭环项与遗留 backlog |
| `pytest-output.txt` | 后端 pytest 原始输出 |
| `frontend-build.txt` | 前端 `tsc -b && vite build` 原始输出 |
| `logs/` | 运行日志（本轮无真机启动，暂空） |
| `screenshots/` | 真机截图（本轮未做浏览器闭环，暂空） |

## 边界声明

- 本轮只改动后端 `workflow_service.py` 与 `test_workflow_service.py`；前端无代码改动。
- 真机导入→识别确认→白名单写入→重开持久化闭环仍待真实 ComfyUI API workflow 样本，本轮未在浏览器闭环，不以服务端测试替代真机验收。
- 指纹规范化（数字 `1`/`1.0`、浮点精度、空值空串、链接 slot 序号等）属行为敏感放宽项，在没有真机样本前未改动，留待 backlog。
