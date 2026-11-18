# TASK-003.1-R37 证据汇总（轻量化归档）

## 范围

M4 第二切片：本地 Ollama 候选生成后端闭环。批量终验节奏，真机验收在阶段收口统一进行。

## 改动

- `backend/llm_client.py`：新增本地 `/api/chat` 非流式调用，保守容错，无云端回退。
- `backend/workflow_api.py`：新增 `POST /api/workflows/{id}/prompt/candidates`、请求模型与消息组装助手。
- `backend/test_workflow_rules.py`：成功且草稿不变、无关规则不泄露、本地失败 502、空模型 422 共 3 个用例。
- 文档：`docs/ROADMAP.md` R37 段、`PROJECT_STATE.md` 第 47 节。

## 口径

- 只传当前工作流已裁剪的相关规则；候选文本不回写工作流、不改草稿。
- 本地模型失败返回 502，不臆造候选；不切云端。

## 测试结果

- 后端：**176 passed, 1 warning in 8.70s**（`pytest-output.txt`；StarletteDeprecationWarning 为遗留告警）。
- 前端：本批无源码改动，未重新构建。

## 边界 / backlog

- 前端模型选择、候选展示、审核后写入、多模式与参数配置、输出结构化验证留后续切片。
