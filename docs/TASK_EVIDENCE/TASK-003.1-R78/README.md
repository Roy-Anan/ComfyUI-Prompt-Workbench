# TASK-003.1-R78 版本快照与当前工作副本 Prompt 只读一致性比对

## 验收范围

- 在历史版本条目上提供「比对当前副本」展开态：分正向 / 负向标注快照文本与当前
  编辑框文本是否一致；不一致时并排只读展示快照文本与当前副本文本。
- **纯前端只读**：不调后端、不写库、不触发恢复；比对仅在前端以 `trim()` 后严格相等
  判定，不做行级 diff、不提供任何写操作入口。
- 基线：`rules=0`、`history=0`、`tasks=0`、`model_identities=16`、草稿文件 0。

## 实现要点（`frontend/src/WorkflowWorkbench.tsx`）

- 新增 `comparingStamp: string | null` 状态，记录当前展开比对的版本戳；打开 / 导入
  工作流时随版本、草稿、恢复态一并清空。
- 每条版本条目在「恢复此版本」旁加「比对当前副本 / 收起比对」切换按钮。
- 展开区块按角色计算：
  - `positiveSame = snapPositive.trim() === positiveText.trim()`
  - `negativeSame = snapNegative.trim() === negativeText.trim()`
  - 一致：仅标注「与当前副本一致」，不展开并排文本。
  - 不一致：标注「与当前副本不一致」，下方分「快照：」「当前：」两行只读展示，
    空文本显示「（空）」。
- 复用既有 `.actions` / `.workflow-meta` / `.muted` 样式，未新增 CSS；未改后端契约。

## 真机闭环（本机 127.0.0.1:17890，PID 17520）

- 工作流 `suyuexisdxlapi.json`（API，1 份真实快照，2026-11-18 03:31:12）：
  - 正向：与当前副本不一致，并排展示快照（较短正向串）与当前副本（追加
    `bench-acceptance-mark` 等后半段）。
  - 负向：与当前副本一致，仅标注、无并排。
  - 截图 `r78-compare-diff.png`。
- 工作流 `r31-compare.json`（API，1 份占位快照，2026-11-18 07:54:10）：
  - 正向：与当前副本不一致，快照 `positive`，当前为候选说明文本；负向：与当前副本
    一致。截图 `r78-compare-placeholder.png`。
- 收起比对后按钮回到「比对当前副本」，比对文本全部消失；全程未点「恢复此版本」，
  未触发任何写入或恢复。
- 结束后库表复核：`workbench_rule=0`、`generation_history=0`、`comfy_task=0`、
  `model_identity=16`，草稿文件 0，回到基线。

## 回归

- 后端：**239 passed, 1 warning**（见 `pytest-output.txt`；与 R77 基线一致，本切片
  未改后端；StarletteDeprecationWarning 为遗留，与本项目无关）。
- 前端：`tsc -b && vite build` 绿（`frontend-build.txt`）；产物
  `index-Bbr-Tz3v.js` 187.69 kB / gzip 59.47 kB，`index-CE0WX0Hl.css` 9.75 kB /
  gzip 2.38 kB。

## 边界与遗留

- 比对口径为整段 `trim()` 后严格相等，不做分词 / 同义词 / 行级差异高亮；空白差异会
  判为不一致。
- 后端 `list_versions` 对 API 格式快照从白名单节点提取 `inputs.text`；UI 格式快照
  节点表为空时文本为空（既有现状，不在本切片改动范围）。
- 版本恢复仍走 R66 既有两步态路径；本切片只做只读比对，不引入回退 / 覆盖语义。
