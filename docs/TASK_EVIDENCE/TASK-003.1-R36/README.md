# TASK-003.1-R36 证据汇总（轻量化归档）

## 范围

M4 第一切片：Ollama 模型只读发现。批量终验节奏，真机验收在阶段收口统一进行。

## 改动

- `backend/main.py`：新增 `fetch_ollama_models` 与 `GET /api/ollama/models`，解析本地 `/api/tags` 模型名。
- `backend/test_main.py`：端点透传在线/离线状态、辅助函数不可达容错共 3 个用例。
- 文档：`docs/ROADMAP.md` R36 段、`PROJECT_STATE.md` 第 46 节。

## 口径

- 只读发现，不触发生成；离线/超时/坏 JSON 保守返回 `online=False` + 空列表 + 错误信息。
- 不切云端、不臆造模型名；前端模型选择控件留 M4 收口批次。

## 测试结果

- 后端：**173 passed, 1 warning in 8.29s**（`pytest-output.txt`；StarletteDeprecationWarning 为遗留告警）。
- 前端：本批无源码改动，未重新构建。

## 边界 / backlog

- 模型选择/参数、候选生成、结构化验证、审核前不写入工作流留后续切片。
