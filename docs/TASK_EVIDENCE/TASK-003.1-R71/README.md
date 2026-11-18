# TASK-003.1-R71 工作副本 Prompt 导出 TXT / JSON

## 验收范围

- 需求基线 E 段：Prompt 支持 TXT 和 JSON 导出。此前历史/诊断/设置/备份已有 JSON 导出，
  工作副本 Prompt 文本本身没有导出入口。本切片补齐导出侧；导入侧（外部文件/粘贴先作候选预览、
  拆分正负向、不覆盖）口径另切片评估。
- 基线：`rules=0`、`history=0`、`tasks=0`、`profiles=13`、`workflows=22`、`model_identities=16`。

## 实现要点（前端 `WorkflowWorkbench.tsx`）

- 模块级 `downloadLocalFile(filename, text, mime)`：Blob + `URL.createObjectURL` + 临时 `<a>`
  点击下载，下载后释放 URL；与既有诊断/设置导出同构，纯本地下载，不写库、不覆盖工作副本。
- 两个入口（编辑框动作区）：
  - 「导出 TXT」：非空正向/负向分段为 `正向：…` / `负向：…`，空段省略；两段以空行分隔。
  - 「导出 JSON」：`{ version: 1, positive, negative }`，保留原文，不改写语法。
- 两侧均空时保守提示「正向与负向均为空，无需导出。」；成功/失败回显消息，不改动编辑框内容。
- 后端无改动；`styles.css` 复用既有按钮样式，未新增规则。

## 真机闭环（本机 127.0.0.1:17890，PID 23740）

- 浏览器选中已确认工作流 `r31-compare.json`，动作区出现「导出 TXT / 导出 JSON」。
- 点击导出 TXT：消息「Prompt 已导出为 TXT（仅本地下载，未写入工作副本）。」；落盘
  `workbench-prompt-202611181053.txt`（199 字节），回读内容正向段/负向段齐全，保留原文。
- 点击导出 JSON：消息「Prompt 已导出为 JSON（仅本地下载，未写入工作副本）。」；console 无报错。
- 环境限制：浏览器对同页第二次下载弹出 multiple_downloads 权限挂起，JSON 文件未在本会话落盘；
  该路径与 TXT 共用同一 `downloadLocalFile`，仅 MIME 与序列化不同，`tsc` 编译通过。获得多下载
  权限后即可落盘；此为浏览器侧权限限制，非代码缺陷。
- 截图：`r71-export-buttons.png`（动作区四按钮与 JSON 导出消息）。
- 验收后已删除下载目录中的临时 `workbench-prompt-*` 文件；stopper 回收 23740（含子进程），
  端口 17890 关闭；Ollama、ComfyUI 未触碰。

## 回归

- 后端：**231 passed, 1 warning**（`pytest-output.txt`；后端无改动，全量回归兜底；
  StarletteDeprecationWarning 为遗留，与本项目无关）。
- 前端：`tsc -b && vite build` 绿（`frontend-build.txt`）；产物
  `index-4-4meC4x.js` 183.70 kB / gzip 58.51 kB，`index-CE0WX0Hl.css` 9.75 kB / gzip 2.38 kB。

## 边界与遗留

- 导入侧（TXT/JSON 读入、粘贴文本先作候选、正负向拆分、预览不覆盖）未实现，留后续切片；
  拆分启发式与候选模型口径需保守，不能识别时整段保留原文。
- 导出不携带模型环境快照、版本号或元数据；如需与历史快照关联，另切片定义。
- 未改动白名单写入、CSRF、回环绑定、unknown 不臆测等安全口径。
