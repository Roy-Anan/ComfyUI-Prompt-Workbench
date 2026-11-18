# TASK-003.1-R68 候选复制按钮 + 诊断数据库完整性巡检字段

## 验收范围

- 两项口径确定、低风险的小切片，不引入新依赖：
  1. M4 候选辅助：本地模型候选面板补「复制候选」按钮，把候选文本写入剪贴板；
     纯前端，不写入工作副本（沿用「候选审核前不写入工作流」口径）。
  2. M9 只读可靠性：诊断报告在数据库连接成功时跑 `PRAGMA integrity_check`，
     响应补 `database.integrity` 字段；连接异常时保守置 `null`，不臆测结果。
- 基线：health `0.1.0-dev.5`；`rules=0`、`history=0`、`tasks=0`、`profiles=13`、
  `workflows=22`、`model_identities=16`；Ollama `127.0.0.1:11434` 在线。

## 实现要点

### 后端（`backend/main.py` / `test_main.py`）

- `/api/diagnostics`：成功打开库连接后执行 `PRAGMA integrity_check`，首行结果串记入
  `database.integrity`（通过为 `ok`，非 ok 原样返回）；既有顶层 `database_error` 保留兼容。
  连接异常时 `database.integrity = null`，不抛出、不 500。
- 测试：既有只读诊断用例补断言 `body["database"]["integrity"] == "ok"`。

### 前端（`frontend/src/WorkflowWorkbench.tsx`）

- `copyCandidate()`：`navigator.clipboard.writeText(candidate)`，成功消息
  「候选已复制到剪贴板（未写入工作副本）。」；失败回显「复制候选失败：…」。
- 候选动作区在「采用到正向 Prompt」旁新增「复制候选」；候选仍为只读，复制不改动编辑框。

## 真机闭环（本机 127.0.0.1:17890，PID 19280）

- 后端直连 `/api/diagnostics`：`database_error=None`，`database.integrity="ok"`；
  计数 rules 0 / history 0 / tasks 0 / model_identities 16 / workflows 22 / profiles 13。
- 浏览器：选中已确认工作流 → 选 `comfyui-prompt:v1` → 生成候选；候选文本只读展示，
  「采用到正向 Prompt」旁出现「复制候选」；点击后消息「候选已复制到剪贴板（未写入工作副本）。」，
  下方编辑框工作副本未被候选覆盖；无 console 报错。
- 截图：`r68-generating.png`（候选生成中）、`r68-copy-candidate.png`（复制成功消息与双按钮）。

## 收尾

- 复制为纯前端剪贴板操作，无后端写入；`rules=0`、`tasks=0`、`history=0` 保持基线。
- stopper 按结构化身份回收实例（PID 19280，含子进程），端口 17890 关闭；Ollama、ComfyUI 未触碰。

## 回归

- 后端：**231 passed, 1 warning**（`pytest-output.txt`；StarletteDeprecationWarning 为遗留，
  与本项目无关）。无新增用例，仅既有诊断用例补完整性断言。
- 前端：`tsc -b && vite build` 绿（`frontend-build.txt`）；产物
  `index-MWBS5jDJ.js` 181.66 kB / gzip 57.92 kB，`index-X0JFovQF.css` 9.42 kB / gzip 2.33 kB。

## 边界与遗留

- 完整性巡检为只读 `integrity_check`；崩溃恢复、自动修复、备份恢复写入与冲突合并仍留后续切片。
- 剪贴板依赖浏览器安全上下文（本机 127.0.0.1 视为安全上下文）；非安全上下文下复制失败会回显错误，不静默。
- 未改动白名单写入、CSRF、回环绑定、unknown 不臆测等安全口径。
