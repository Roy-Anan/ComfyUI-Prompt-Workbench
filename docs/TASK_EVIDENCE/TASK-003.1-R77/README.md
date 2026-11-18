# TASK-003.1-R77 草稿载入回填名称备注 + 更新支持改名改备注

## 验收范围

- 补全 R76 更新闭环的名称 / 备注缺口：
  - 载入草稿时，除正/负向 Prompt 外，把草稿原名称与备注回填到顶部草稿名称 / 备注输入框。
  - 更新既有草稿时，提交框内当前名称与备注（可改），不再强制沿用草稿原值；名称非空由
    前端先校验，同名撞名由后端 400 映射。
- 更新仍不写入工作副本、不动版本快照；复用 R74 `draft_id` 更新路径。
- 基线：`rules=0`、`history=0`、`tasks=0`、`model_identities=16`。

## 实现要点（`frontend/src/WorkflowWorkbench.tsx`）

- `adoptDraft`：回填 `positiveText/negativeText` 之外，补 `setDraftName(draft.name)`、
  `setDraftNote(draft.note)`。
- `updateDraft`：名称取 `draftName.trim()`，空则前端提示「请先填写草稿名称。」；备注取
  `draftNote.trim()`；`POST` 带 `draft_id`、框内名称、当前正/负向、框内备注。
- 说明文案改为：载入后可在上方名称 / 备注框修改，更新时用当前编辑框内容与名称备注一并
  覆盖该草稿。
- 后端补契约测试 `test_draft_update_changes_name_and_note_without_self_collision`：
  更新可改名 / 改备注，自身旧名不构成同名冲突；改成与另一条草稿同名仍被 400 拒绝
  （同名去重只排除自身）。

## 真机闭环（本机 127.0.0.1:17890，PID 11720）

- 选中已确认白名单工作流 `r31-compare.json`；保存草稿「旧名」（备注「旧备注」，正向
  「p1 旧名正向」）。
- 载入草稿：正向回填「p1 旧名正向」，顶部名称框回填「旧名」、备注框回填「旧备注」。
- 改名「新名」、改备注「新备注」、改正向「p2 新名正向」；点草稿行「更新」进入两步态
  「确认更新？」/「取消」（`r77-rename-confirm.png`）。
- 确认后列表记录为：名称「新名」、备注「新备注」、正向「p2 新名正向」；旧名不再出现，
  提示「草稿已更新（未写入工作副本）。」（`r77-renamed.png`）。
- 清理：两步态删除后回到空态；结束后文件核对 `drafts/` 文件数为 0。

## 回归

- 后端：**239 passed, 1 warning**（见 `pytest-output.txt`；较 R76 基线 238 新增 1 条
  改名 / 改备注 + 自身不撞名用例；StarletteDeprecationWarning 为遗留，与本项目无关）。
- 前端：`tsc -b && vite build` 绿（`frontend-build.txt`）；产物
  `index-BfKybwQ2.js` 187.03 kB / gzip 59.32 kB，`index-CE0WX0Hl.css` 9.75 kB /
  gzip 2.38 kB。
- 真机库复核：`workbench_rule=0`、`generation_history=0`、`comfy_task=0`、
  `model_identity=16`，草稿文件 0，回到基线。

## 边界与遗留

- 更新改名受后端同名去重约束：同一工作流内不得与其他草稿重名；草稿名称长度 ≤120、
  备注 ≤1000 沿用既有校验。
- 收藏、标签、跨工作流复制、回收站、环境快照、历史双向索引、历史反向创建草稿等仍留
  后续切片。未改动白名单写入、CSRF、回环绑定、unknown 不臆测等安全口径。
