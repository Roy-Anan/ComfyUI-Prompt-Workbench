# TASK-003.1-R9 证据目录

M3 第四切片：规则记录结构、三级继承与冲突/未知判定骨架。

## 交付物

- `backend/rule_engine.py`：纯函数规则解析层（RuleRecord、三级继承、冲突/未知判定、上下文批量解析、规则盘点）。
- `backend/test_rule_engine.py`：8 个单元用例。

## 切片边界

- 本轮不读文件系统、不调 ComfyUI/Ollama、不回写工作流；无新 HTTP 接口与前端改动。
- 规则持久化存储、旧 profiles 文本结构化导入、多模型/LoRA 规则组合、冲突人工裁决界面、动态检索、LLM 上下文组装留后续切片。

## 验收记录

| 项 | 结果 |
| --- | --- |
| 后端 pytest | 88 passed, 1 warning（见 `pytest-output.txt`） |
| 前端构建 | tsc -b && vite build exit 0（见 `frontend-build.txt`） |
| 解析样本 | `samples/rule-resolution.json` |

## 目录

- `pytest-output.txt`：全量后端 pytest 原始输出。
- `frontend-build.txt`：前端构建原始输出。
- `samples/rule-resolution.json`：三级继承 + 未知字段解析快照。
- `git-diff.md` / `git-diff-raw.txt`：本切片代码差异。
- `execution-report.md`、`test-results.md`、`environment-report.md`、`known-issues.md`：归档说明。
