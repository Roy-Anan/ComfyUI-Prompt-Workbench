# Doubao 回执 — TASK-003.1-R29

## 任务

M3 第二十四切片：多 latent / CLIP 跳过层节点保守标注。此前 latent 与 Clip Skip 解析只保留首个命中节点，多节点工作流中其余节点被静默丢弃；本切片沿用 R25 多采样器组范式，全量列出且不替选。

## 完成内容

- `backend/workflow_service.py`：API/UI 两段在顶层 `latent`、`clip_skip`（取首个）之外，新增 `latent_nodes`、`clip_skip_nodes` 全量列表并进入返回 report。
- `backend/workflow_api.py`：`_sampler_actuals` 透传 `latent_node_count`/`latent_nodes`、`clip_skip_node_count`/`clip_skip_nodes`；旧 report 无列表字段时计数缺省，向后兼容。
- `backend/test_workflow_service.py`：新增双 latent、双 CLIPSetLastLayer 用例，断言顶层取首、列表全量、clip_skip 序列 [2, 3]。
- `frontend/src/WorkflowWorkbench.tsx`：比对摘要区对多节点给出保守提示（结论取首个，其余未参与比对）。
- 文档：`PROJECT_STATE.md` 第 39 节、`docs/ROADMAP.md` 回填 R29。

## 口径

- 顶层事实与比对结论仍对应首个命中节点；其余节点如实列入列表，不合并、不替选、不猜测取舍。

## 自测结果

- 后端：**165 passed, 1 warning in 6.03s**。
- 前端：`tsc -b && vite build` exit 0；`index-BaTB97FZ.js 162.27 kB │ gzip 52.51 kB`。
- 真机浏览器（`samples/compare-payload.json`）：双 latent 节点 6（832×1216）、10（768×1152）；双 CLIP 节点 8（clip_skip 2）、11（clip_skip 3）；registered，计数 无法判定 17 / 匹配 2 / 不在集合 1；Clip Skip 2=2、Steps 25=25 匹配。截图 `screenshots/compare-multi-nodes.png`。
- 清理后规则表 0 条。

## 排查记录

- 首轮比对误报 unregistered：脚本按文件名子串 `"pony"` 选档案，命中同族 AutismMix；改为按完整 filename 精确匹配后 registered。后端解析与匹配链路无缺陷。

## Git

- 功能提交：`5a38de24dd9a1364271cee404391a828e32aaba0`（本地 dev，已推送 origin/dev）。
- 远端核对：连接器 `list_commits(dev)` 最新提交即 `5a38de2`，消息「feat(workbench): M3 第二十四切片 多 latent/CLIP 节点保守标注」，作者 Roy-Anan / 1538072315@qq.com。
- main 分支未改动。

## 边界

- 多 latent / 多 CLIP 链路的节点取舍、跨节点冲突裁决与逐节点比对留后续切片。
