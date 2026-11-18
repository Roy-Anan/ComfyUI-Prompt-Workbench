# TASK-003.1-R26 证据目录

M3 第二十一切片：前端规则比对结果只读展示。

## 交付物

- `frontend/src/WorkflowWorkbench.tsx`：比对面板类型、状态与拉取逻辑；只读展示注册状态、checkpoint、架构、计数、实际参数摘要与逐条比对条目。
- `frontend/src/styles.css`：比对面板布局与状态徽标配色（match 绿 / out_of_range、out_of_set 橙 / unknown 灰）。

## 口径

- 面板数据来自 `GET /api/workflows/{id}/rules/compare`，纯只读。
- 不做规则勾选/驳回、差异预览或规则写入；unknown 条目原样展示后端理由。

## 验收记录

| 项 | 结果 |
| --- | --- |
| 后端 pytest | 164 passed, 1 warning（见 `pytest-output.txt`） |
| 前端构建 | tsc -b && vite build exit 0（见 `frontend-build.txt`） |
| 真机浏览器 | `screenshots/compare-panel-meta.png`、`screenshots/compare-entries.png`；载荷 `samples/compare-payload.json` |
