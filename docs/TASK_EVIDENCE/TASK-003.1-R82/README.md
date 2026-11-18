# TASK-003.1-R82 草稿收藏星标（可逆标记）

## 验收范围

- 草稿记录新增可逆的 `favored` 布尔标记；旧草稿文件无该字段时按 `false` 处理。
- 收藏切换**不改变**现有按 `updated_at` 倒序的列表排序（不引入置顶语义），
  也**不 bump** `updated_at`；更新草稿时**保留**既有收藏状态。
- 收藏为可逆轻量操作，直接切换，不走删除那样的两步态确认。
- 基线：`rules=0`、`history=0`、`tasks=0`、`model_identities=16`、草稿文件 0。

## 实现要点

后端（`backend/workflow_service.py`、`backend/workflow_api.py`）：

- `list_drafts` 投影增加 `"favored": bool(record.get("favored") or False)`。
- `save_draft`：新建记录 `favored=False`；更新路径 `setdefault("favored", False)`，
  保留既有收藏值，不被保存覆盖。
- 新增 `toggle_favored(workflow_id, draft_id)`：读取草稿文件翻转 `favored` 后原子写回，
  不动工作副本、版本快照与 `updated_at`；文件不存在抛 `WorkflowError("指定的草稿不存在")`。
- 新增端点 `POST /api/workflows/{workflow_id}/drafts/{draft_id}/favorite`，
  错误类型元组与其他草稿端点一致（`WorkflowError, FileNotFoundError, OSError`）。

前端（`frontend/src/WorkflowWorkbench.tsx`）：

- `DraftEntry` 增加 `favored?: boolean`。
- 新增 `toggleFavorite(draft)`：调用收藏端点后 `loadDrafts` 刷新；按钮文案未收藏「收藏」、
  已收藏「取消收藏」，纯文本，不使用图标字符。
- 排序仍由后端按更新时间倒序返回，前端不做置顶重排；未新增 CSS。

## 真机闭环（本机 127.0.0.1:17890，PID 18584）

- 工作流 `r31-compare.json`（API，白名单已确认）：保存草稿「R82 收藏验收」，
  行内按钮顺序为 载入到编辑框 / 收藏 / 更新 / 删除，未收藏态显示「收藏」
  （`r82-before-favorite.png`）。
- 点「收藏」→ 按钮翻为「取消收藏」，提示「已收藏草稿「R82 收藏验收」。」；
  刷新页面并重选工作流后收藏态仍在（持久化落盘）。
- 载入回填名称备注后走更新两步态确认更新，收藏态保留，按钮仍为「取消收藏」
  （`r82-favored.png`，底部提示「草稿已更新（未写入工作副本）」）。
- 点「取消收藏」→ 按钮翻回「收藏」，提示「已取消收藏草稿「R82 收藏验收」。」；
  两步态删除后草稿箱回到空态「还没有保存的草稿。」。
- 全程未点「写入工作副本并校验」，未触发 ComfyUI 提交；结束后库表复核回到基线，
  草稿文件计数 0。

## 回归

- 后端：**241 passed, 1 warning**（见 `pytest-output.txt`；较 R81 基线 239 新增 2 个
  收藏用例：service 层翻转/保留/不存在，API 层端点翻转/持久化/不存在；
  StarletteDeprecationWarning 为遗留，与本项目无关）。
- 前端：`tsc -b && vite build` 绿（`frontend-build.txt`）；产物
  `index-Byqy5wVp.js` 191.15 kB / gzip 60.51 kB，`index-CE0WX0Hl.css` 9.75 kB /
  gzip 2.38 kB。

## 边界与遗留

- 收藏仅作关注标记，不参与排序、不提供按收藏筛选/分组/置顶；这些需求留后续切片再定口径。
- 收藏状态随草稿文件落盘；备份/导出链路是否纳入 `favored` 字段，在后续备份切片核对。
- 草稿 F 段其余范围（标签、跨工作流复制、回收站、模型环境快照、对话上下文/锁定片段、
  与生成历史双向索引、历史反向创建草稿）均在最小闭环之外，未在本切片实现。
