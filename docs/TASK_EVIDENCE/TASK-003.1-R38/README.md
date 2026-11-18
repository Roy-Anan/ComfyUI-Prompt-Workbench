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

## 真机验收（阶段收口，2026-11-18）

受控浏览器打开 `127.0.0.1:17890`，既有 API 样本 `r31-compare.json` 走完整闭环：

- 候选面板下拉列出本地 Ollama 模型 `comfyui-prompt:v1`、`qwen3:latest`。
- 生成候选返回只读文本；未登记工作流上下文为空，模型按现有字段保守回复，未臆造参数。
- “采用到正向 Prompt”回填正向编辑框，负向保持原值不变；候选未自动写入工作副本。
- 既有审核写入链路通过：1 个 Prompt 节点变化，非白名单字段完整性校验通过。
- 截图：`screenshots/candidate-panel.png`。
- 验收后规则表为 0（本次未导入档案）；后端进程已回收。

## 边界 / backlog

- 三种创作模式、模型参数配置、输出结构化验证、候选多版本对比留后续切片。
