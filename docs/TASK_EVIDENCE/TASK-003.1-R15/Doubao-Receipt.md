# Doubao 回执 — TASK-003.1-R15

## 任务

ComfyUI Prompt Workbench，M3 第十切片：生成参数值结构化解析（本地 FastAPI + React 免安装本机 Web）。

## 执行结果

- 新增 `value_normalize.py` 纯函数层：Steps/CFG/Clip Skip 解析为 value/range/floor；Resolution 解析为 resolutions 列表；Sampler/Scheduler 解析为 list；解析失败保留原文、`structured=None`，不臆测。
- 候选记录附 `structured`；规则表新增 `structured_json` 列（旧库 ALTER 补列），`value_json` 仍存原始裸值，引擎 `record.value` 原样返回口径不变；导入链路透传结构化落库并回读。
- 后端 pytest **118 passed**（1 条既有 StarletteDeprecationWarning）；前端 `tsc -b && vite build` exit 0（33 模块）。
- 真机闭环：IntoRealism_Ultra_V8 导入 16 条、0 拒绝，Steps/CFG/Resolution/Sampler 结构化正确回读，清理归零，见 `samples/smoke-structured.json`。

## 交付边界

- 仅覆盖六类生成参数；结构化结果尚未接前端展示或参数比对/冲突检测。
- 未对接 Ollama 对话生成（M4）、ComfyUI 出图对接（M6）；未改动 main 分支，改动落在 dev。

## 提交信息

- 分支：`dev`
- 提交：`645024bc8ba78c75d5a3463d9efcda5b44c66cfd`（本地 commit，已推送 origin/dev，连接器核对远端 dev 最新即此提交）。
- 基线：`45f12e2`（R14 回执回填）。
