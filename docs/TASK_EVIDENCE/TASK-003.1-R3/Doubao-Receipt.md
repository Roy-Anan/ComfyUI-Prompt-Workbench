# Doubao 回执 — TASK-003.1-R3（原始回执，未摘录润色）

## 一句话结论

在 R2 基础上完成工作流服务的追溯修复、结构化白名单 diff 改造与 5 个回归用例补齐；后端 **62 passed**，前端构建 **exit 0**。真机闭环仍待真实 ComfyUI API workflow 样本，本轮未在浏览器验收。

## 执行前基线

- 仓库：`D:\AI\ComfyUI-Prompt-Workbench-Git`，远端 `https://github.com/Roy-Anan/ComfyUI-Prompt-Workbench`
- `dev = origin/dev = 2729fc8695e970bda29ca44bafee029d926a59e2`
- main：`3084866aa85595133c7a1179b15ddd71e659d8f3`，未合并、未改动
- 工作区干净

## 本轮做了什么

### 1. 中转 conditioning 节点追溯修复（`backend/workflow_service.py`）

- 新增 `CONDITIONING_PASSTHROUGH_MARKERS`（ConditioningCombine / ConditioningConcat / ConditioningSetArea / ConditioningSetAreaPercentage / ConditioningSetAreaStrength / ConditioningAverage / ConditioningMask / ConditioningZeroOut / ConditioningDrop / ConditioningBias）与 `CONDITIONING_INPUT_KEYS`。
- 新增 `_is_conditioning_passthrough(class_type)`。
- `_trace_api_encoders`：
  - 文本编码器：沿全部输入向上追溯（原行为不变）。
  - 中转节点：只沿 conditioning 类输入（白名单键名，或 `conditioning` 开头的编号键，如 `conditioning_1/2`）继续压栈；不再把 clip/model 链接误当 conditioning 上游。
- 修复前：经 `ConditioningCombine` 合并的正向条件在中转节点处被当成叶子，追溯断裂，文本节点角色识别不到。

### 2. 结构化白名单 diff（`backend/workflow_service.py`）

- 新增 `_structure_diff(original, candidate, allowed_paths, prefix)`：dict / list / 标量递归比对，返回不在白名单路径内的差异；路径形如 `6.inputs.seed`、`<node_id>.inputs.text`。
- 写入前校验：还原白名单文本后由整对象 `!=` 改为 `_structure_diff(original, working, allowed_paths)`。
- 写入后回滚校验：由整对象 `!=` 改为 `_structure_diff(original, verified, allowed_paths)`。
- 安全口径未降低：键集合不一致、列表长度不一致、类型不一致、白名单外任一标量变化，仍拒绝写入；白名单路径仅限各确认节点的 `inputs.text`。

### 3. 回归测试补齐（`backend/test_workflow_service.py`，新增 5 例）

- `test_detect_api_workflow_wrapped_in_nodes`：`nodes` 字典包装 API 结构识别与角色判定。
- `test_passthrough_conditioning_node_trace_continues_upstream`：KSampler positive → ConditioningCombine → ConditioningZeroOut → CLIPTextEncode，正向节点可追溯命中。
- `test_version_snapshot_keeps_previous_prompt_text`：连续两次写入，两份快照分别保存写入前旧文本、第一次写入后文本。
- `test_reimport_and_reopen_persists_across_store_instances`：同一数据目录重建 `WorkflowStore`，Prompt 文本、确认状态、列表均可读回；原始文件未被修改。
- `test_structural_diff_rejects_non_whitelist_value_change`：非白名单字段 `steps` 被拒绝。

## 测试与构建结果

- 后端：`.venv\Scripts\python.exe -m pytest -q` → **62 passed, 1 warning in 6.95s**，exit 0。
  - 警告：`StarletteDeprecationWarning`（httpx + starlette.testclient 既有遗留，非本轮引入）。
- 前端：`npm run build`（`tsc -b && vite build`）→ **exit 0**，33 modules，Vite 5.4.21。
- 原始输出：`pytest-output.txt`、`frontend-build.txt`。

## 明确未完成 / 未验证

- 真机浏览器闭环：导入真实 API workflow → 识别确认 → 白名单写入 → 重开持久化 → 快照校验，本轮未执行；缺真实样本，未伪造通过。
- 指纹规范化偏严格问题本轮刻意未放宽（数字 1/1.0、浮点精度、空值空串、链接 slot 序号），列入 backlog，待真实样本确认安全口径后再改。
- 模型/LoRA 真机识别、真实出图端到端、显存阈值测量不在本轮边界。
- Python 3.12 兼容性未验证（本机仅 3.13.18）。

## 改动文件

- 修改：`backend/workflow_service.py`、`backend/test_workflow_service.py`
- 新增证据：`docs/TASK_EVIDENCE/TASK-003.1-R3/`（README、Doubao-Receipt、execution-report、test-results、environment-report、git-diff、git-diff-raw.txt、known-issues、pytest-output.txt、frontend-build.txt、logs/、screenshots/）

## 环境

- Windows 本机 ROY；Python 3.13.18（项目 `.venv`）；pytest 8.4.2；Node v22.23.2；npm 10.9.8；Vite 5.4.21。
