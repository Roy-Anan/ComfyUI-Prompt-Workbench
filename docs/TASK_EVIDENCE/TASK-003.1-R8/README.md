# TASK-003.1-R8 证据目录

## 任务范围

M3「模型身份库与规则引擎」第三切片：**同 SHA256 多路径身份归并**。

在 R7 身份库骨架上，把同类别内持有相同 SHA256 的多个文件映射为同一身份：`identity_group` 返回身份键 `category:digest`、摘要与副本列表；`identity_summary` 回挂 `identity_key`、`copy_count`、`copies`。未哈希文件身份键为空，不做哈希推断。

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
| `samples/merge-summary.json` | 真机身份组与副本归并快照 |
| `screenshots/` | 真机浏览器验收截图 |
| `logs/` | 运行日志（本轮无留存需要，暂空） |

## 边界声明

- 归并仅按类别内摘要匹配；跨类别不合并；文件移动后按身份重新定位留后续切片。
- 规则继承、规则来源/可信度/版本/回退、规则组合与冲突检测、动态检索、云端资料导入审核未实现。
- 未对接 Ollama 对话生成（M4）、ComfyUI 出图对接（M6）；未改动 main 分支，改动落在 dev。
