# TASK-003.1-R79 工作副本 Prompt 文件导入（解析预览，不覆盖编辑框）

## 验收范围

- 补齐 R71 导出 TXT/JSON 的对称导入侧：选择本地 TXT/JSON 文件，前端解析为正/负向
  进入本地只读预览；**采用后才填入编辑框**，放弃则清除；不调后端、不写库、在采用前
  不覆盖现有编辑框内容。
- 基线：`rules=0`、`history=0`、`tasks=0`、`model_identities=16`、草稿文件 0。

## 实现要点（`frontend/src/WorkflowWorkbench.tsx`）

- 模块级 `parsePromptImport(filename, text)`：
  - `.json`：按导出格式对称解析为对象，取字符串 `positive`/`negative`；非对象、数组、
    JSON 语法错误或两侧均空保守抛错。
  - `.txt` / 纯文本：按行首 `正向：` / `负向：`（兼容全角冒号）分段；无任一标记时整段
    归正向，负向留空；两侧均空抛错。
- 新增本地状态 `importedPrompt`；`onPromptFileChosen` 读取文件并解析，成功进预览、
  失败回显保守错误；`adoptImported` 填入正/负向编辑框后清除预览；`dismissImported`
  仅清除预览。
- 编辑面板动作区加「导入 TXT/JSON」隐藏文件入口；预览区块为只读 textarea +
  「采用到编辑框」「放弃导入」。打开 / 导入工作流时随既有状态一并清空。
- 纯前端，未改后端契约；复用既有 `.actions` / `.workflow-text-field` /
  `.workflow-field-head` / `.muted` 样式，未新增 CSS。

## 真机闭环（本机 127.0.0.1:17890，PID 18800）

- 工作流 `r31-compare.json`（API，白名单已确认）：
  - 上传 `prompt-sample.json`：预览正向「导入正向 JSON, 1girl, sofa, natural light,
    masterpiece」、负向「导入负向 JSON, cartoon, anime, 3d render, cgi」；编辑框原有
    候选说明文本与 `negative` 未被覆盖（`r79-import-json-preview.png`）。
  - 「放弃导入」：预览清除，编辑框保持原样。
  - 上传 `prompt-sample.txt`：按标记分段，预览正向/负向为 TXT 样本；「采用到编辑框」
    后两侧填入编辑框、预览清除（`r79-adopted.png`）。
  - 上传 `prompt-plain.txt`（无标记）：整段归正向，预览仅正向块、无负向块。
  - 上传 `prompt-bad.json`（非法 JSON）：提示「导入失败：Error: JSON 文件无法解析。」，
    既有预览保留未被替换，编辑框不变（`r79-import-bad.png`）。
- 全程未点「写入工作副本并校验」，未触发后端写接口；结束后库表复核回到基线。

## 回归

- 后端：**239 passed, 1 warning**（见 `pytest-output.txt`；与 R78 基线一致，本切片
  未改后端；StarletteDeprecationWarning 为遗留，与本项目无关）。
- 前端：`tsc -b && vite build` 绿（`frontend-build.txt`）；产物
  `index-Ch7-O8oM.js` 189.81 kB / gzip 60.07 kB，`index-CE0WX0Hl.css` 9.75 kB /
  gzip 2.38 kB。

## 边界与遗留

- 导入仅采信本地文件解析结果；粘贴文本导入、多文件合并、导入前与现有编辑框的差异
  预览留后续切片。
- 无标记纯文本保守归正向，不猜测负向；JSON 非导出结构（如工作流 JSON）按无效
  Prompt 文件拒绝，不臆造字段。
- 采用只填前端编辑框，落库仍走既有「写入工作副本并校验」白名单链路。
