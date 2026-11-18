# TASK-003.1-R29 证据目录

M3 第二十四切片：多 latent / CLIP 跳过层节点保守标注。

## 交付物

- `backend/workflow_service.py`：API/UI 两段解析在顶层 `latent`、`clip_skip`（取首个节点）之外，新增 `latent_nodes`、`clip_skip_nodes` 全量列表。
- `backend/workflow_api.py`：`_sampler_actuals` 透传节点计数与摘要（`latent_node_count`/`latent_nodes`、`clip_skip_node_count`/`clip_skip_nodes`）。
- `backend/test_workflow_service.py`：双 latent、双 CLIPSetLastLayer 解析断言。
- `frontend/src/WorkflowWorkbench.tsx`：多节点摘要提示，结论取首个、其余未参与比对。

## 口径

- 顶层事实与比对结论仍对应首个命中节点；其余节点如实列入列表，不合并、不替选、不猜测取舍。
- 旧 report 缺少列表字段时计数缺省，向后兼容。

## 验收记录

| 项 | 结果 |
| --- | --- |
| 后端 pytest | 165 passed, 1 warning（见 `pytest-output.txt`） |
| 前端构建 | tsc -b && vite build exit 0（见 `frontend-build.txt`） |
| 真机浏览器 | `screenshots/compare-multi-nodes.png`；载荷 `samples/compare-payload.json` |
