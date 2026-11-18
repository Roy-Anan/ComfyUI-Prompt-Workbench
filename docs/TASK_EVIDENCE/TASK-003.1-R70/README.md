# TASK-003.1-R70 工作副本 Prompt 复制（正向 / 负向 / 完整）

## 验收范围

- 需求基线 E 段：支持复制正向、负向、完整正负向，保留原语法。此前仅候选文本可复制
  （R68），工作副本编辑框没有复制入口。本切片补齐，纯前端剪贴板，不改编辑框、不写库。
- 基线：health `0.1.0-dev.5`；`rules=0`、`history=0`、`tasks=0`、`profiles=13`、
  `workflows=22`、`model_identities=16`。

## 实现要点（前端 `WorkflowWorkbench.tsx` / `styles.css`）

- 通用 `copyPromptText(text, label)`：空文本保守提示「…为空，无需复制。」；成功写入剪贴板并
  回显「… 已复制到剪贴板（未写入工作副本）。」；失败回显「复制 … 失败：…」。不转义、不改写
  原语法，不改动编辑框内容。
- 三个入口：
  - 正向 Prompt 标题行「复制正向」→ 复制 `positiveText`；
  - 负向 Prompt 标题行「复制负向」→ 复制 `negativeText`；
  - 动作区「复制完整」→ 非空的正/负向以 `正向：…` / `负向：…` 分段拼接；两侧均空提示无需复制。
- `styles.css`：新增 `.workflow-field-head`（标题与按钮两端对齐）与紧凑按钮尺寸；沿用既有色板。
- 后端无改动；中英文对照复制依赖未实现的中文编辑/翻译区，留后续切片。

## 真机闭环（本机 127.0.0.1:17890，PID 11296 → 重启 16480）

- 浏览器选中已确认工作流 `r31-compare.json`，编辑框出现「复制正向 / 复制负向 / 复制完整」。
- 依次点击：正向消息「正向 Prompt 已复制到剪贴板（未写入工作副本）。」；负向「负向 Prompt 已
  复制…」；完整「完整 Prompt 已复制…」。三次点击后编辑框工作副本内容均未被覆盖，console 无报错。
- 截图：`r70-editor-buttons.png`（三按钮布局）、`r70-copy-positive.png`（正向复制消息）、
  `r70-copy-both.png`（完整复制消息）、`r70-final.png`（复核带空格文案终态）。

## 收尾

- 复制为纯前端剪贴板操作，无后端写入；规则/历史/任务计数保持基线。
- stopper 按结构化身份回收实例（11296、16480，含子进程），端口 17890 关闭；Ollama、ComfyUI 未触碰。

## 回归

- 后端：**231 passed, 1 warning**（`pytest-output.txt`；后端无改动，全量回归兜底；
  StarletteDeprecationWarning 为遗留，与本项目无关）。
- 前端：`tsc -b && vite build` 绿（`frontend-build.txt`）；产物
  `index-DpHK1Jto.js` 182.84 kB / gzip 58.29 kB，`index-CE0WX0Hl.css` 9.75 kB / gzip 2.38 kB。

## 边界与遗留

- 不复制中英文对照（中文编辑/翻译区未实现）；不做 TXT/JSON 导入导出、区块拆分与锁定片段，留后续。
- 剪贴板依赖浏览器安全上下文（本机 127.0.0.1 视为安全上下文）；非安全上下文下失败回显错误，不静默。
- 未改动白名单写入、CSRF、回环绑定、unknown 不臆测等安全口径。
