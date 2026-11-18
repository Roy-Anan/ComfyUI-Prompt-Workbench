# TASK-003.1-R75 前端命名草稿箱 UI（列出 / 保存 / 载入 / 删除）

## 验收范围

- 对接 R74 多命名草稿后端，在工作区编辑面板之后提供草稿箱：手动保存当前编辑框的正/负向
  Prompt 组合，可载入回编辑框、可两步态删除。草稿保存不写入工作副本。
- 基线：`rules=0`、`history=0`、`tasks=0`、`profiles=13`、`workflows=22`、`model_identities=16`。

## 实现要点（`WorkflowWorkbench.tsx`）

- 类型 `DraftEntry`：`id/name/positive/negative/note/created_at/updated_at`；导入补 `apiDelete`。
- 状态：`drafts`、`draftName`、`draftNote`、`draftBusy`、`deletingDraftId`。
- `openWorkflow` / `importFile`：重置草稿状态并 `loadDrafts(id)`。
- `loadDrafts`：`GET /api/workflows/{id}/drafts`，失败置空。
- `saveDraft`：空名 / 两侧 Prompt 均空时前端先提示；`POST` 后清空名称备注并刷新列表，
  回显「草稿已保存（未写入工作副本）。」。
- `adoptDraft`：把草稿正/负向填入编辑框 `positiveText/negativeText`，**不直接写工作副本**，
  回显「草稿已载入编辑框（尚未写入工作副本）。」。
- `deleteDraft`：两步态；`DELETE` 后刷新列表。
- 草稿箱面板挂在可写编辑面板之后、ComfyUI 任务面板之前；复用既有 class，未新增 CSS。

## 真机闭环（本机 127.0.0.1:17890，PID 17816）

- 选中已确认白名单工作流 `r31-compare.json`；草稿箱空态面板在位：标题「草稿箱」、说明、
  草稿名称 / 备注输入框、「保存当前为草稿」按钮、空态文案「还没有保存的草稿。」
  （`r75-draft-empty.png`）。
- 填入名称「头像方向一」、备注「R75 验收草稿」并保存：草稿出现在列表，显示名称、正向摘要、
  负向摘要与备注；名称 / 备注输入框已清空（`r75-draft-saved.png`）。
- 载入验证：先在正向编辑框留标记 `LOAD_MARKER_TEST`，点「载入到编辑框」后正向回填为草稿
  原文；载入只改编辑框，未触发工作副本写入。
- 删除验证：点「删除」出现两步态「确认删除？」/「取消」；确认后列表清空，回到空态
  （`r75-draft-deleted.png`）。
- 文件核对（工作流目录 `c618d3c7-dbfc-4e60-828b-e4241991b26d`）：
  - `working.json` SHA256 在保存 / 载入 / 删除全程保持不变；
  - `versions/` 始终 1 份，未因草稿操作新增快照；
  - 删除后 `drafts/` 文件数为 0。

## 回归

- 后端：**237 passed, 1 warning**（见 `../TASK-003.1-R74/pytest-output.txt`；全量回归兜底，
  StarletteDeprecationWarning 为遗留，与本项目无关）。
- 前端：`tsc -b && vite build` 绿（`frontend-build.txt`）；产物
  `index-CIw_k3nE.js` 185.93 kB / gzip 59.05 kB，`index-CE0WX0Hl.css` 9.75 kB / gzip 2.38 kB。

## 边界与遗留

- 载入仅回填编辑框；写入工作副本仍需用户在编辑面板点「写入工作副本并校验」，沿用既有
  白名单与校验路径。
- 收藏、标签、搜索、跨工作流复制、回收站、环境快照、历史双向索引等复杂能力留后续切片。
- 未改动白名单写入、CSRF、回环绑定、unknown 不臆测等安全口径。
