# Doubao 回执 — TASK-003.1-R23

## 任务

M3 第十八切片：Resolution 解析保留括号内尺寸。R21 的尾部备注剥离误伤了括号内的分辨率本体；本切片让 Resolution 在原始文本上提取 `W×H` 并去重，数值/列表字段维持备注剥离口径。

## 完成内容

- `backend/value_normalize.py`：`normalize_resolution` 提取后按 (宽,高) 去重；`normalize()` 对 Resolution 传原始 raw，其余字段传 cleaned。
- 测试：括号内三组尺寸提取、重复尺寸去重。
- 文档：`PROJECT_STATE.md` 第 33 节、`docs/ROADMAP.md` 回填 R23。

## 自测结果

- 后端：**158 passed, 1 warning in 5.81s**。
- 前端：`tsc -b && vite build` exit 0；`index-IXKUmsZF.js 156.95 kB`、CSS 5.44 kB。
- 真机冒烟（`samples/smoke-res-paren.json`）：
  - 导入 HuslyoRealismSDXL_v3 档案 20 条、0 拒绝。
  - Resolution 括号内 `{768×1152, 648×1152, 864×1152}` 结构化；Clip Skip `2（非 V3 独立参数）`→value 2；Steps `30~32`→range；Scheduler `Karras`→list。
  - 清理后规则表 0 条。

## 保守边界

- 分号两套建议（示例/指南）未分组；散文型 Resolution 无 `W×H` 时 structured=None，保持 unknown。
- 括号内非尺寸备注仍留在 raw，不参与结构化。

## Git

- 功能提交：`5f8788f367b79002dfa74cec8e0839f66cbc8c25`（本地 dev，已推送 origin/dev）。
- 远端核对：连接器 `list_commits(dev)` 最新提交即 `5f8788f`，消息「feat(rules): M3 第十八切片 Resolution 解析保留括号内尺寸」，作者 Roy-Anan / 1538072315@qq.com。
- main 分支未改动。

## 边界

- 两套建议分组、多 latent/多采样器组比对在后续切片。
