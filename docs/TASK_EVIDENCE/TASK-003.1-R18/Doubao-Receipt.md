# Doubao 回执 — TASK-003.1-R18

## 任务

M3 第十三切片：把 R17 归集的上下文规则装配为可下发给本地 LLM 的裁剪提示载荷。继承优先级由程序确定，字段保留来源层级/来源/可信度/版本；冲突与未知如实标注，未注册模型空载荷，不臆造。

## 完成内容

- `backend/rule_prompt.py`（新增）：`build_prompt_context(context)`，注册上下文经引擎三级继承解析，输出 `{status, checkpoint, architecture, fields, conflicts, unknown, instruction}`；`resolved` 带 `source`，`conflict` 带 `sources` 与说明；未注册返回空字段集与禁止猜测指令。
- `backend/rule_engine.py`：`resolve_field`/`resolve_context` 增加可选 `architecture_scope`，显式区分 checkpoint 作用域与架构家族作用域。
- `backend/workflow_api.py`：`GET /api/workflows/{workflow_id}/rules/prompt`。
- `backend/test_rule_prompt.py`（3 例）、`backend/test_workflow_rules.py`（补 2 例接口断言）。
- 文档：`PROJECT_STATE.md` 第 28 节、`docs/ROADMAP.md` 回填 R18。

## 自测结果

- 后端：**127 passed, 1 warning in 5.52s**（新增 5 passed）。
- 前端：`tsc -b && vite build` exit 0；`index-IXKUmsZF.js 156.95 kB`、CSS 5.44 kB。
- 真机冒烟（`samples/smoke-prompt.json`）：
  - 导入 IntoRealism 档案 16 条、0 拒绝。
  - `suyuexisdxlapi.json` → `intorealismUltra_v80.safetensors`；载荷 16 字段（14 checkpoint + 2 architecture/SDXL 1.0），conflicts=[]、unknown=[]；Steps=6~12，source=checkpoint，confidence=authoritative。
  - `ghost_missing.safetensors` → unregistered，0 字段。
  - 清理后规则表 0 条。

## 过程修正

- 首跑架构/全局字段 `source_level=None`：引擎把 checkpoint 作用域同时当架构作用域检索，架构规则落在不同 scope_key 被漏掉；增加 `architecture_scope` 显式传参后修正。
- `resolve_context` 返回引擎对象，键取属性访问而非下标。

## Git

- 功能提交：`5180f17f8e903d4d8fc412acf8ed6727fe778e6a`（本地 dev，已推送 origin/dev）。
- 远端核对：连接器 `list_commits(dev)` 最新提交即 `5180f17`，消息「feat(rules): M3 第十三切片上下文规则装配为 LLM 裁剪提示」，作者 Roy-Anan / 1538072315@qq.com。
- main 分支未改动。

## 边界

- 只装配载荷；未调用 Ollama、未发送提示、未回写工作流（M4 接入）。
- LoRA 规则组合、冲突人工裁决界面、载荷裁剪长度控制、动态检索、前端规则界面在后续切片。
