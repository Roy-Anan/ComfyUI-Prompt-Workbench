# Doubao 回执 — TASK-003.1-R14

## 任务

ComfyUI Prompt Workbench，M3 第九切片：档案候选审核导入规则库（本地 FastAPI + React 免安装本机 Web）。

## 执行结果

- `profile_source.import_profile()`：单份档案候选导入为 checkpoint 级规则；落库前引擎 `RuleRecord.validate()` 校验，非法候选跳过记 rejected；无完整 checkpoint 文件名 400 拒绝。
- `main.py` 新增 `POST /api/profiles/import`，走本地会话与 CSRF 中间件；404/400 分别处理；导入报告含 imported/rejected/unknown_fields。
- 后端 pytest **112 passed**（1 条既有 StarletteDeprecationWarning）；前端 `tsc -b && vite build` exit 0（33 模块）。
- 真机闭环：Anything_V5 导入 11 条、0 拒绝、引擎解析回读 resolved、清理归零，见 `samples/smoke-import.json`。

## 交付边界

- 仅 checkpoint 级导入；architecture/global 级装载、参数结构化、逐候选审核界面、前端规则/档案管理界面未实现。
- 未对接 Ollama 对话生成（M4）、ComfyUI 出图对接（M6）；未改动 main 分支，改动落在 dev。

## 提交信息

- 分支：`dev`
- 提交：`e83b41e8e040821af545f3b5f30a36532f8e5ba2`（本地 commit，已推送 origin/dev，连接器核对远端 dev 最新即此提交）。
- 基线：`e0c13ca`（R13 回执回填）。
