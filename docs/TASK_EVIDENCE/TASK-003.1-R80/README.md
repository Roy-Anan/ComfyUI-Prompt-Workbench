# TASK-003.1-R80 粘贴文本导入（解析预览，复用 R79 隔离口径）

## 验收范围

- 在 R79 文件导入之外补粘贴入口：编辑面板内联文本框，粘贴内容解析为正/负向进入与
  文件导入共用的本地只读预览；采用才填编辑框，放弃清除；不调后端、不写库、采用前
  不覆盖现有编辑框。
- 基线：`rules=0`、`history=0`、`tasks=0`、`model_identities=16`、草稿文件 0。

## 实现要点（`frontend/src/WorkflowWorkbench.tsx`）

- 解析层重构：抽出 `parsePromptJson`（导出 JSON 取字符串 `positive/negative`）与
  `parsePromptText`（标记分段，无标记整段归正向）；`parsePromptImport` 按文件后缀分流。
- 新增 `parsePromptContent(text)` 供粘贴使用：以 `{` 开头先尝试导出 JSON，结构不符或
  语法错误回退纯文本分段，不臆造字段。
- 状态 `pasteOpen` / `pasteText`；`parsePasted` 解析成功进预览并收起粘贴面板、清空
  粘贴框，失败回显保守错误；`cancelPaste` 收起清空。打开 / 导入工作流时随既有状态一并
  清空。
- 动作区加「粘贴文本」切换按钮；粘贴面板为 textarea + 「解析到预览」「取消」。复用既有
  `.actions` / `.workflow-text-field` / `.workflow-field-head` / `.muted` 样式，未新增
  CSS；纯前端，未改后端契约。

## 真机闭环（本机 127.0.0.1:17890，PID 3268）

- 工作流 `r31-compare.json`（API，白名单已确认）：
  - 粘贴带 `正向：/负向：` 标记的 TXT：预览正向「粘贴正向 TXT, 1girl, window light,
    soft smile」、负向「粘贴负向 TXT, cartoon, anime, text」；编辑框原有候选说明文本与
    `negative` 未被覆盖（`r80-paste-txt-preview.png`）。
  - 粘贴导出 JSON 文本：走 JSON 分支，预览两侧为 JSON 正/负向字段；编辑框未被覆盖。
  - 粘贴 `{` 开头的坏文本：JSON 解析失败回退纯文本分段，无标记整段归正向，预览仅
    正向块、无负向块（`r80-paste-fallback.png`）。
- 采用 / 放弃路径复用 R79 同一 `importedPrompt` 预览态，不再重复真机验证。
- 全程未点「写入工作副本并校验」，未触发后端写接口；结束后库表复核回到基线。

## 回归

- 后端：**239 passed, 1 warning**（见 `pytest-output.txt`；与 R79 基线一致，本切片
  未改后端；StarletteDeprecationWarning 为遗留，与本项目无关）。
- 前端：`tsc -b && vite build` 绿（`frontend-build.txt`）；产物
  `index-D9bi9hyy.js` 190.65 kB / gzip 60.33 kB，`index-CE0WX0Hl.css` 9.75 kB /
  gzip 2.38 kB。

## 边界与遗留

- 粘贴不读取系统剪贴板（`navigator.clipboard.readText` 权限在本机环境不保证可用），
  由用户手动粘贴到内联框；多文件合并、导入前与现有编辑框差异预览留后续切片。
- 粘贴的非导出 JSON（如工作流 JSON）在 `{` 开头时 JSON 结构校验失败，回退纯文本分段，
  不臆造正向/负向字段。
