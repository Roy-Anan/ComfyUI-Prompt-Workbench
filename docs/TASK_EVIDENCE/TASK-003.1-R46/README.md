# TASK-003.1-R46 证据汇总（轻量化归档）

## 范围

M7 第一切片：生成历史快照与图片索引。批量终验节奏，真机验收在阶段收口统一进行。

## 改动

- `backend/generation_history.py`（新）：`generation_history` 表；提交时刻固化 Prompt/模型快照；终态回写状态与图片文件名元数据。
- `backend/workflow_api.py`：提交端点落快照；校准循环同步历史状态，成功回写图片索引。
- `backend/main.py`：`GET /api/history`（可按 `workflow_id` 过滤）、`GET /api/history/{prompt_id}` 只读端点。
- `backend/test_generation_history.py`（新）：6 个用例。
- 文档：`docs/ROADMAP.md` R46 段、`PROJECT_STATE.md` 第 56 节。

## 口径

- 图片只记文件名/子目录/类型元数据，`exists` 留空（输出目录配置未接入，不臆造存在）；不复制原图。
- 快照在提交时刻固化，不随后续草稿改动变化；未识别的模型保持缺省，不补默认值。

## 测试结果

- 后端：**212 passed, 1 warning in 17.24s**（`pytest-output.txt`；遗留 StarletteDeprecationWarning）。

## 边界 / backlog

- 图片磁盘存在性探测、时间轴/图库双视图、搜索筛选导出、历史反向创建草稿、缩略图索引留后续切片。
