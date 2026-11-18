# TASK-003.1-R38 证据汇总（轻量化归档）

## 范围

M4 第三切片：工作区前端模型选择与候选审核闭环。批量终验节奏，真机验收在阶段收口统一进行。

## 改动

- `frontend/src/WorkflowWorkbench.tsx`：新增候选类型与状态、模型列表拉取、候选生成、候选只读展示与“采用到正向”。
- 文档：`docs/ROADMAP.md` R38 段、`PROJECT_STATE.md` 第 48 节。

## 口径

- 候选只填入编辑框，不自动写入工作副本；落库仍走既有审核写入链路。
- 本地 Ollama 离线/无模型时保守提示，不臆造候选；不切云端。

## 测试结果

- 后端：**176 passed, 1 warning in 8.57s**（`pytest-output.txt`；遗留 StarletteDeprecationWarning）。
- 前端：`tsc -b` 无报错，`vite build` 绿（`index-B7xvjVEX.js 167.20 kB gzip 53.74 kB`，见 `frontend-build.txt`）。

## 边界 / backlog

- 三种创作模式、模型参数配置、输出结构化验证、候选多版本对比留后续切片。
