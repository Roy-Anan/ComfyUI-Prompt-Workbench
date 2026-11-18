# TASK-003.1-R72 候选放弃 / 清除入口

## 验收范围

- 需求基线 D 段：候选可比较、接受、放弃、手动删除。此前候选仅有「采用到正向 Prompt」与
  「复制候选」，没有放弃/清除入口。本切片补齐放弃动作；多候选比较、逐候选勾选/驳回属 M4
  复杂交互，口径另切片评估。
- 基线：`rules=0`、`history=0`、`tasks=0`、`profiles=13`、`workflows=22`、`model_identities=16`。

## 实现要点（前端 `WorkflowWorkbench.tsx`）

- `dismissCandidate()`：清空本地 `candidate` 状态，回显「候选已放弃（未写入工作副本）。」；
  纯前端状态重置，不写库、不调用后端、不改动编辑框工作副本。
- 候选动作区在「采用到正向 Prompt」「复制候选」旁补「放弃候选」；候选为空时该区整体不渲染。
- 后端无改动；未新增样式规则，沿用既有按钮样式。

## 真机闭环（本机 127.0.0.1:17890，PID 21196）

- Ollama 在线（`comfyui-prompt:v1`、`qwen3:latest`）；选中已确认工作流 `r31-compare.json`，
  点「生成候选」返回候选，候选区三按钮在位（采用 / 复制 / 放弃）。
- 点「放弃候选」：候选区整体消失，消息「候选已放弃（未写入工作副本）。」；下方编辑框工作副本
  正/负向原文保持不变，console 无报错。
- 截图：`r72-candidate-before.png`（候选态三按钮）、`r72-candidate-dismissed.png`（放弃后
  候选区清除、工作副本未变）。
- 验收后 stopper 回收 21196（含子进程），端口 17890 关闭；Ollama、ComfyUI 未触碰。

## 回归

- 后端：**231 passed, 1 warning**（`pytest-output.txt`；后端无改动，全量回归兜底；
  StarletteDeprecationWarning 为遗留，与本项目无关）。
- 前端：`tsc -b && vite build` 绿（`frontend-build.txt`）；产物
  `index-BDZ7dr_2.js` 183.78 kB / gzip 58.55 kB，`index-CE0WX0Hl.css` 9.75 kB / gzip 2.38 kB。

## 边界与遗留

- 放弃仅清除当前单候选显示；不删除后端任务记录、不清理历史。多候选列表、比较与逐候选驳回留后。
- 候选采用仍只写入正向 Prompt；负向候选与结构化验证留后续切片。
- 未改动白名单写入、CSRF、回环绑定、unknown 不臆测等安全口径。
