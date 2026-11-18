# Doubao 回执 — TASK-003.1-R22

## 任务

M3 第十七切片：Resolution 规则对接实际 latent 尺寸比对。从工作流提取 latent 节点宽高，Resolution 结构化规则与实际 (宽,高) 整数集合保守匹配；读不到尺寸或规则无结构化时归 unknown，不臆测近似匹配。

## 完成内容

- `backend/workflow_service.py`：`LATENT_MARKERS`、`_latent_size()`；API/UI 两段识别 LatentImage 节点并把首个有效尺寸写入报告 `latent`。
- `backend/workflow_api.py`：`_sampler_actuals` 合并 latent width/height 到比对 actuals。
- `backend/rule_compare.py`：`_compare_resolutions` 宽高整数集合匹配；缺宽/高或非数值归 unknown/actual_missing；resolutions 不再复用字符串 list 匹配。
- 测试：latent 提取/缺失、actuals 宽高注入、Resolution match/out_of_set/缺尺寸 unknown。
- 文档：`PROJECT_STATE.md` 第 32 节、`docs/ROADMAP.md` 回填 R22。

## 自测结果

- 后端：**156 passed, 1 warning in 5.75s**。
- 前端：`tsc -b && vite build` exit 0；`index-IXKUmsZF.js 156.95 kB`、CSS 5.44 kB。
- 真机冒烟（`samples/smoke-resolution.json`）：
  - 导入 IntoRealism 档案 17 条、0 拒绝。
  - 报告 latent `{node_id:6, width:704, height:1024}`，analysis.json 持久化并回读一致。
  - actuals 含 width 704 / height 1024；Resolution 规则 {896×1152, 832×1216}，实际 704×1024 → out_of_set。
  - 清理后规则表 0 条。

## 保守边界

- 仅取首个有效 latent 节点；多 latent 节点取舍、多采样器组逐组比对未实现。
- 括号内分辨率、分号两套建议分组结构化未实现；散文型 Resolution structured=None，保持 unknown。

## Git

- 功能提交：`cb7d8225c923d8f831e490729f0f54da5381d79e`（本地 dev，已推送 origin/dev）。
- 远端核对：连接器 `list_commits(dev)` 最新提交即 `cb7d822`，消息「feat(rules): M3 第十七切片 Resolution 规则对接实际 latent 尺寸比对」，作者 Roy-Anan / 1538072315@qq.com。
- main 分支未改动。

## 边界

- 多 latent/多采样器组、括号内分辨率提取、两套建议分组在后续切片。
