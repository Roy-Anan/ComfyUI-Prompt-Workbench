# 执行报告 — TASK-003.1-R3

## 1. 基线核对

- 提交前 `dev = origin/dev = 2729fc8`，工作区干净；main `3084866` 未动。
- 通读 `backend/workflow_service.py`、`backend/workflow_api.py`、`backend/test_workflow_service.py`、`frontend/src/WorkflowWorkbench.tsx` 与 R2 `known-issues.md`，确认 5 类改进点的边界。

## 2. 代码改动

### 2.1 中转 conditioning 追溯（`workflow_service.py`）

- 新增 `CONDITIONING_PASSTHROUGH_MARKERS`：`ConditioningCombine`、`ConditioningConcat`、`ConditioningSetArea(Percentage/Strength)`、`ConditioningAverage`、`ConditioningMask`、`ConditioningZeroOut`、`ConditioningDrop`、`ConditioningBias`。
- 新增 `CONDITIONING_INPUT_KEYS` 与 `_is_conditioning_passthrough`。
- `_trace_api_encoders` 调整：
  - 文本编码器沿全部输入向上追溯（保持原行为）；
  - 中转节点只沿 conditioning 类输入（键名在白名单或以 `conditioning` 开头，含 `conditioning_1/2` 编号键）继续压栈，不再把模型/CLIP 链接误当成 conditioning 上游。
- 修复点：此前 `ConditioningCombine` 等中转节点被当成叶子节点，导致经其合并的正向条件追溯断裂。

### 2.2 结构化白名单 diff（`workflow_service.py`）

- 新增 `_structure_diff(original, candidate, allowed_paths, prefix)`：递归比对 dict / list / 标量，返回不在白名单路径内的差异；路径形如 `6.inputs.seed`、`<node_id>.inputs.text`。
- 写入前完整性校验：由「把白名单文本还原后整对象 `!=` 原始」改为 `_structure_diff(original, working, allowed_paths)`。
- 写入后回滚校验：由「整对象 `!=` 原始」改为 `_structure_diff(original, verified, allowed_paths)`。
- 安全强度未降：键集合不一致、列表长度不一致、类型不一致、任一标量变化，只要落在白名单之外仍拒绝；白名单路径仍仅限各确认节点的 `inputs.text`。

### 2.3 测试补齐（`test_workflow_service.py`）

新增用例：

- `test_detect_api_workflow_wrapped_in_nodes`：`nodes` 字典包装结构识别与角色判定。
- `test_passthrough_conditioning_node_trace_continues_upstream`：经 `ConditioningCombine` → `ConditioningZeroOut` 的正向条件可追溯到文本节点。
- `test_version_snapshot_keeps_previous_prompt_text`：连续两次写入，两份快照分别保存写入前旧文本与第一次写入后文本。
- `test_reimport_and_reopen_persists_across_store_instances`：同一数据目录重建 `WorkflowStore` 后，Prompt 文本、确认状态、列表均可持久化读回，原始文件未被修改。
- `test_structural_diff_rejects_non_whitelist_value_change`：非白名单字段（`steps`）被结构化 diff 拒绝。

## 3. 未改动项

- 前端组件、API 路由、数据目录与迁移逻辑未改。
- 指纹规范化偏严格问题未放宽（见 `known-issues.md`）。
- 真实出图端到端、模型/LoRA 真机识别不在本轮边界。
