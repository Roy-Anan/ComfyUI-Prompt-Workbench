# Doubao 回执 — TASK-003.1-R19

## 任务

M3 第十四切片：把规则库已结构化的生成参数与工作流采样器实际参数做保守比对；两侧可读才给结论，不可判定归 unknown，不推断匹配或冲突。

## 完成内容

- `backend/workflow_service.py`：新增 `_sampler_params()`，采样器组补 `params` 快照（steps/cfg/sampler_name/scheduler/denoise），API 与 UI 两条解析路径均提取。
- `backend/rule_compare.py`（新增）：`compare_rule()`/`compare_workflow()`；数值 range/floor/value 判定，列表/分辨率集合匹配；非数值实际、未结构化规则、不可比字段、冲突/未知规则归 unknown 并给 reason。
- `backend/rule_prompt.py`：字段条目携带 `structured` 供比对层使用。
- `backend/workflow_api.py`：`GET /api/workflows/{workflow_id}/rules/compare` 与 `_sampler_actuals()`。
- `backend/test_rule_compare.py`（8 例）、`backend/test_workflow_rules.py`（补 2 例接口断言）。
- 文档：`PROJECT_STATE.md` 第 29 节、`docs/ROADMAP.md` 回填 R19。

## 自测结果

- 后端：**137 passed, 1 warning in 5.81s**（新增 10 passed）。
- 前端：`tsc -b && vite build` exit 0；`index-IXKUmsZF.js 156.95 kB`、CSS 5.44 kB。
- 真机冒烟（`samples/smoke-compare.json`）：
  - 导入 IntoRealism 档案 16 条、0 拒绝；重新导入 R5 API 样本。
  - 实际参数：steps 35、cfg 5.5、sampler_name dpmpp_2m_sde、scheduler karras。
  - Steps → out_of_range(6~12)；CFG → out_of_range(1.5~2)；Sampler → out_of_set；Scheduler 带备注未结构化 → unknown；其余非参数字段 unknown。
  - 清理后规则表 0 条。

## 过程修正

- 首跑真机 params 为空：现存副本是改动前导入的缓存报告，重开不重新解析；重新导入样本后 params 正常。
- 比对顺序：先判规则状态，再判字段可比性，再判规则是否结构化，最后进入数值/集合判定。

## Git

- 功能提交：`516821ba89aa74c557a166488d6c0398fdeb9dbe`（本地 dev，已推送 origin/dev）。
- 远端核对：连接器 `list_commits(dev)` 最新提交即 `516821b`，消息「feat(rules): M3 第十四切片结构化规则值与工作流实际参数保守比对」，作者 Roy-Anan / 1538072315@qq.com。
- main 分支未改动。

## 边界

- 比对只读，不回写工作流、不触发 LLM、不生成修正建议。
- 仅 Steps/CFG/Clip Skip/Sampler/Scheduler；Resolution 与 latent 尺寸未对接；VAE/CLIP 参数未纳入；多采样器组未逐组比对；前端比对展示界面未实现。
