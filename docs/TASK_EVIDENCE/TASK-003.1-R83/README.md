# TASK-003.1-R83 草稿收藏可见性配套（仅看收藏过滤 + 已收藏标注）

## 验收范围

- 草稿箱增加「仅看收藏」只读勾选，与既有关键词过滤 **AND** 组合；草稿名称旁对已收藏项
  显示「已收藏」标注。纯前端视图增强，**后端零改动**，不改列表排序、不置顶。
- 勾选偏好为会话态，不写后端、不做本地持久化；切换工作流时随草稿箱一并复位。
- 基线：`rules=0`、`history=0`、`tasks=0`、`model_identities=16`、草稿文件 0。

## 实现要点（`frontend/src/WorkflowWorkbench.tsx`）

- 新增会话状态 `favoredOnly`（默认 `false`）；`filteredDrafts` 在关键词过滤前先叠加
  `favoredOnly && !draft.favored` 排除条件。
- 过滤行关键词输入框旁复用既有 `.workflow-meta` 样式加勾选框；草稿行名称后对
  `draft.favored` 渲染 `<small className="workflow-meta">已收藏</small>`。
- 两处草稿箱重置路径（切换工作流 / 载入比对）一并复位 `favoredOnly`；未新增 CSS、
  未改后端契约与测试。

## 真机闭环（本机 127.0.0.1:17890，PID 15692）

- 工作流 `r31-compare.json`（API，白名单已确认）：保存两条草稿——「R83 收藏甲」已收藏、
  「R83 普通乙」未收藏。未过滤态两条并列，甲名称下带「已收藏」标注、按钮「取消收藏」，
  乙无标注、按钮「收藏」（`r83-both.png`）。
- 勾选「仅看收藏」后仅显收藏甲，乙被过滤（`r83-favored-only.png`）；保持勾选、关键词
  搜「乙」命中空态「没有匹配的草稿。」（AND 组合生效）；取消勾选、清空关键词后两条
  回显。
- 两条草稿经两步态删除后草稿箱回到空态；全程未写入工作副本、未提交 ComfyUI 任务。
- 结束后库表复核回到基线，草稿文件计数 0。

## 回归

- 后端：**241 passed, 1 warning**（见 `pytest-output.txt`；本切片未改后端，基线与 R82
  一致；StarletteDeprecationWarning 为遗留，与本项目无关）。
- 前端：`tsc -b && vite build` 绿（`frontend-build.txt`）；产物
  `index-DaBk07Po.js` 191.43 kB / gzip 60.57 kB，`index-CE0WX0Hl.css` 9.75 kB /
  gzip 2.38 kB。

## 边界与遗留

- 勾选偏好未接入 M10 本地界面偏好记忆，刷新页面后复位；如需跨会话记忆留后续切片。
- 收藏分组、置顶、按收藏导出仍不在本切片范围；备份/导出链路是否纳入 `favored` 字段
  留后续备份切片核对。
