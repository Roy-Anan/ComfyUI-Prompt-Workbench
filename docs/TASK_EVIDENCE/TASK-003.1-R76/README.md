# TASK-003.1-R76 草稿箱关键词本地过滤 + 已有草稿更新入口

## 验收范围

- 在 R75 草稿箱基础上补两项最小闭环能力：
  - **关键词本地过滤**：按草稿名称 / 备注 / 正向 / 负向 Prompt 做大小写不敏感的
    包含匹配，纯前端即时过滤，不写库、不调后端。
  - **已有草稿更新**：草稿行两步态「更新」，把当前编辑框的正/负向 Prompt 覆盖到既有
    草稿，保留草稿原名称与备注；复用 R74 后端已就绪的 `draft_id` 更新路径。
- 过滤与更新都不写入工作副本；更新不改动版本快照。
- 基线：`rules=0`、`history=0`、`tasks=0`、`model_identities=16`。

## 实现要点（`frontend/src/WorkflowWorkbench.tsx`）

- 新增状态：`updatingDraftId`（更新两步态锚定草稿）、`draftKeyword`（过滤关键词）。
- `openWorkflow` / `importFile` 两处重置点同步清空 `draftKeyword`、重置
  `updatingDraftId`。
- `filteredDrafts`：`draftKeyword.trim().toLowerCase()` 为空时全量；否则对
  `name + note + positive + negative` 拼接串做小写包含匹配。
- `updateDraft(draft)`：两侧 Prompt 均空时前端先提示；`POST` 草稿端点带
  `draft_id`、原 `name`、当前编辑框正/负向、原 `note`；成功后刷新列表并回显
  「草稿已更新（未写入工作副本）。」。
- 空态三分支：无草稿（`还没有保存的草稿。`）、有关键词但无匹配（`没有匹配的草稿。`）、
  列表；关键词输入框仅在已有草稿时显示。
- 草稿行更新按钮两步态：「更新」→「确认更新？」/「取消」；与既有删除两步态互不干扰。
- 后端补契约测试 `test_draft_update_preserves_name_and_note`：沿用原名称 / 原备注、
  只覆盖正/负向，断言名称与备注保留、正/负向被覆盖。

## 真机闭环（本机 127.0.0.1:17890，PID 18400）

- 选中已确认白名单工作流 `r31-compare.json`；草稿箱空态在位（`r76-draft-empty.png`）。
- 保存两条不同名称草稿：「草稿-方向甲」（备注「过滤验证甲」，正向「甲草稿正向初始」）、
  「草稿-方向乙」（备注「过滤验证乙」，正向「乙草稿正向初始」）；列表双条在位
  （`r76-two-drafts.png`）。
- 过滤：关键词「甲」仅显草稿甲（`r76-filter-match.png`）；无匹配关键词
  「zzz不存在」显示「没有匹配的草稿。」（`r76-filter-none.png`）；清空后两条恢复。
- 载入：点草稿甲「载入到编辑框」，编辑框回填甲草稿原文，未触发工作副本写入。
- 更新：改正向为「甲草稿正向已更新」，点草稿甲「更新」出现两步态「确认更新？」/
  「取消」（`r76-update-confirm.png`）；确认后草稿甲正向被覆盖为新文本，名称
  「草稿-方向甲」与备注「过滤验证甲」保留，草稿乙未变（`r76-updated.png`）。
- 清理：两条草稿均经两步态删除，列表回到空态；结束后文件核对 `drafts/` 文件数为 0。

## 回归

- 后端：**238 passed, 1 warning**（见 `pytest-output.txt`；较 R75 基线 237 新增 1 条
  更新保留契约用例；StarletteDeprecationWarning 为遗留，与本项目无关）。
- 前端：`tsc -b && vite build` 绿（`frontend-build.txt`）；产物
  `index-DL-hWSDp.js` 186.94 kB / gzip 59.29 kB，`index-CE0WX0Hl.css` 9.75 kB /
  gzip 2.38 kB。
- 真机库复核：`workbench_rule=0`、`generation_history=0`、`comfy_task=0`、
  `model_identity=16`，草稿文件 0，回到基线。

## 边界与遗留

- 本次更新只覆盖正/负向 Prompt，不支持在更新流程里改名 / 改备注；改名、改备注、
  收藏、标签、跨工作流复制、回收站、环境快照、历史双向索引、历史反向创建草稿等
  复杂能力留后续切片。
- 过滤为前端本地关键词包含匹配，未做分词 / 拼音 / 同义词；搜索范围仅当前工作流草稿。
- 未改动白名单写入、CSRF、回环绑定、unknown 不臆测等安全口径。
