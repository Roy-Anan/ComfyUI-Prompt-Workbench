# TASK-003.1-R47 证据汇总（轻量化归档）

## 范围

历史图片磁盘存在性标注。批量终验节奏，真机验收在阶段收口统一进行。

## 改动

- `backend/datadir.py`：`OPTIONAL_EXTERNAL_KEYS` 与默认设置纳入可选 `output` 目录。
- `backend/generation_history.py`：`annotate_exists` 按输出目录核对图片存在性，未配置记 None，越出目录按丢失。
- `backend/main.py`：历史列表/详情端点返回时实时标注 `exists`。
- `backend/test_generation_history.py`：3 个用例。
- 文档：`docs/ROADMAP.md` R47 段、`PROJECT_STATE.md` 第 57 节。

## 口径

- 只核对文件存在性，不复制、不移动原图；文件丢失历史记录保留并标记不存在。

## 测试结果

- 后端：**215 passed, 1 warning in 16.86s**（`pytest-output.txt`；遗留 StarletteDeprecationWarning）。

## 边界 / backlog

- 缩略图索引、时间轴/图库双视图、搜索筛选导出、历史反向创建草稿留后续切片。
