# Doubao 回执 — TASK-003.1-R10

## 任务

ComfyUI Prompt Workbench，M3 第五切片：规则 SQLite 持久化与检索接口骨架（本地 FastAPI + React 免安装本机 Web）。

## 执行结果

- 新增 `backend/rule_store.py`：`workbench_rule` 表（level/scope_key/rule_key 唯一，value JSON 往返）；upsert/查/删/装载/解析；写入前 `RuleRecord.validate()` 校验。
- `main.py` 初始化规则表；新增 `GET /api/rules`（清单过滤）与 `GET /api/rules/resolve`（只解析请求键，冲突/未知如实上报，非法层级/空键 400）。`client` fixture 抽到 `conftest.py`。
- 后端 pytest **98 passed**（1 条既有 StarletteDeprecationWarning）；前端 `tsc -b && vite build` exit 0（33 模块），本轮无前端代码改动。
- 真机冒烟：空清单 200；空规则未知字段全 unknown；坏层级/空键 400，见 `samples/smoke-rules.json`。

## 交付边界

- 本轮只做持久化与只读检索；规则写入/导入 HTTP 接口、旧 profiles 结构化入库、前端规则管理界面未实现。
- 多模型/LoRA 规则组合、冲突人工裁决、动态检索、LLM 上下文组装、版本/差异回退未实现。
- 未对接 Ollama 对话生成（M4）、ComfyUI 出图对接（M6）；未改动 main 分支，改动落在 dev。

## 提交信息

- 分支：`dev`
- 提交：`caad8539c25503d887162f69bbfd73d7dad06603`（本地 commit，已推送 origin/dev，连接器核对远端 dev 最新即此提交）。
- 基线：`a28f259`（R9 回执回填）。
