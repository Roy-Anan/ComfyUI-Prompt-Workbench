# Doubao 回执 — TASK-003.1-R26

## 任务

M3 第二十一切片：前端规则比对结果只读展示。后端比对结论此前不可见，本切片在工作流工作区新增只读面板呈现。

## 完成内容

- `frontend/src/WorkflowWorkbench.tsx`：`ComparisonEntry` / `ComparePayload` 类型、`compare` 状态、`loadCompare(id)` 拉取 `/api/workflows/{id}/rules/compare`；面板展示注册状态、Checkpoint、架构、计数徽标、实际参数摘要与逐条比对条目。
- `frontend/src/styles.css`：面板布局与 match / out_of_range / out_of_set / unknown 四档配色。
- 文档：`PROJECT_STATE.md` 第 36 节、`docs/ROADMAP.md` 回填 R26。

## 口径

- 纯只读：不做规则勾选/驳回、差异预览或规则写入；unknown 条目原样展示后端理由。
- 未登记工作流显示提示，不猜测参数。

## 自测结果

- 后端：**164 passed, 1 warning in 6.14s**（本切片无后端逻辑改动，回归全绿）。
- 前端：`tsc -b && vite build` exit 0；`index-BUphuMzW.js 158.94 kB │ gzip 51.58 kB`。
- 真机浏览器（`samples/compare-payload.json`）：
  - 状态已登记；Checkpoint ponyDiffusionV6XL_v6.safetensors；架构 Pony / SDXL 系。
  - 计数 unknown 18 / match 2；摘要步数 25、CFG 7、Clip Skip 2、832×1216。
  - Clip Skip 2=2 匹配、Steps 25=25 匹配；其余 unknown 带理由。
  - 截图 `screenshots/compare-panel-meta.png`、`screenshots/compare-entries.png`；清理后规则表 0 条。

## Git

- 功能提交：`feace310763fd7c0fde1328ae64caaabeb66b232`（本地 dev，已推送 origin/dev）。
- 远端核对：连接器 `list_commits(dev)` 最新提交即 `feace31`，消息「feat(workbench): M3 第二十一切片 前端规则比对结果只读展示」，作者 Roy-Anan / 1538072315@qq.com。
- main 分支未改动。

## 边界

- 规则候选勾选/驳回、差异预览、冲突人工裁决与规则管理界面为后续切片；`sampler_groups` 多组摘要尚未在前端展开。
