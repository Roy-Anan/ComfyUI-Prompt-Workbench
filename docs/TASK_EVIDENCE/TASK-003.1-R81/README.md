# TASK-003.1-R81 编辑框字数统计与上限只读提示

## 验收范围

- 正/负向编辑框头部显示当前字符数与后端上限（对齐 `MAX_PROMPT_CHARS=200_000`）；
  超过上限时追加「已超上限」标注。纯只读提示，不做前端硬拦截，写入校验仍以后端
  白名单链路为准。
- 基线：`rules=0`、`history=0`、`tasks=0`、`model_identities=16`、草稿文件 0。

## 实现要点（`frontend/src/WorkflowWorkbench.tsx`）

- 模块级常量 `PROMPT_MAX_CHARS = 200_000`，注释标明与后端 `workflow_service.MAX_PROMPT_CHARS`
  对齐；辅助函数 `promptCountLabel(text)` 返回 `当前 / 上限`，超长追加标注。
- 正/负向 `workflow-field-head` 标题旁以既有 `.muted` 样式展示计数，复制按钮位置不变；
  未新增 CSS、未改后端契约。

## 真机闭环（本机 127.0.0.1:17890，PID 12948）

- 工作流 `r31-compare.json`（API，白名单已确认）：正向计数 `77 / 200000`、负向
  `8 / 200000`，与实际文本长度一致；计数位于标题旁、复制按钮靠右，布局正常
  （`r81-char-count.png`）。
- 超上限分支未在真机构造 20 万字符文本实测；标注逻辑由 `len > MAX` 条件与 tsc 审查
  保证，前端不拦截输入。
- 全程未点「写入工作副本并校验」，未触发后端写接口；结束后库表复核回到基线。

## 回归

- 后端：**239 passed, 1 warning**（见 `pytest-output.txt`；与 R80 基线一致，本切片
  未改后端；StarletteDeprecationWarning 为遗留，与本项目无关）。
- 前端：`tsc -b && vite build` 绿（`frontend-build.txt`）；产物
  `index-D-IWCzWq.js` 190.85 kB / gzip 60.42 kB，`index-CE0WX0Hl.css` 9.75 kB /
  gzip 2.38 kB。

## 边界与遗留

- 计数按 JS `string.length`（UTF-16 码元），与后端 Python `len(str)` 对 BMP 字符一致；
  组合 emoji / 代理对边界不另行换算。Token 估算、按词/分段统计留后续切片。
