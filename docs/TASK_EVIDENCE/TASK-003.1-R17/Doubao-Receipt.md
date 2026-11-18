# Doubao 回执 — TASK-003.1-R17

## 任务

M3 第十二切片：按工作流 checkpoint 匹配规则上下文并三级继承解析。把当前工作流识别出的 checkpoint 文件名与规则库精确匹配，只回传本上下文相关的 checkpoint / architecture / global 规则；未识别或未登记模型返回 unregistered、空规则集，不臆造。

## 完成内容

- `backend/rule_store.py`
  - `context_for_checkpoint(connection, checkpoint)`：返回 `{status, checkpoint, architecture, checkpoint_rules, architecture_rules, global_rules}`；无关 checkpoint 规则不外泄。
  - `_checkpoint_architecture(records, checkpoint)`：先在 checkpoint 桶找 Base Architecture，回退 architecture 桶同键记录；与架构 scope 做相等/前缀/包含匹配。
- `backend/workflow_api.py`
  - `_database_path()`：`datadir.database_path(default_data_root())`。
  - `_checkpoint_filename(report)`：取 `ckpt_name`/`unet_name`。
  - `GET /api/workflows/{workflow_id}/rules`：无识别 checkpoint → `unregistered` + `reason=no_checkpoint_recognized`；有文件名 → `context_for_checkpoint`。
- `backend/test_workflow_rules.py`：3 例（注册上下文继承架构规则、未知 checkpoint 未登记、无 checkpoint 未识别）。
- 文档：`PROJECT_STATE.md` 第 27 节、`docs/ROADMAP.md` 回填 R17。

## 自测结果

- 后端：**122 passed, 1 warning in 5.52s**（新增 3 passed）。
- 前端：`tsc -b && vite build` exit 0；`index-IXKUmsZF.js 156.95 kB`、`index-CTOHglX0.css 5.44 kB`。
- 真机冒烟（`samples/smoke-context.json`）：
  - 导入 IntoRealism 档案 16 条、0 拒绝。
  - `suyuexisdxlapi.json` → `intorealismUltra_v80.safetensors`；上下文 14 checkpoint + 2 architecture(SDXL 1.0) + 0 global。
  - `ghost_missing.safetensors` → unregistered。
  - 清理后规则表 0 条。

## 过程修正

- 首跑架构规则 0 条：Base Architecture 事实在 R16 已分流到架构级，checkpoint 桶无记录；`_checkpoint_architecture` 增加架构桶回退查找。
- 首跑清理漏删架构桶残留；改为拉全量规则后逐条删除，真机库清 0。

## Git

- 功能提交：`6a194418c81f9dc15f6a328c0b76cca42ebdc4b7`（本地 dev，已推送 origin/dev）。
- 远端核对：连接器 `list_commits(dev)` 最新提交即 `6a19441`，消息「feat(rules): M3 第十二切片工作流 checkpoint 规则上下文检索」，作者 Roy-Anan / 1538072315@qq.com。
- main 分支未改动。

## 边界

- 仅按 checkpoint 匹配；启用 LoRA 规则组合未纳入（暂无 LoRA 规则来源）。
- 上下文只归集规则，尚未装配为发给 LLM 的裁剪提示；冲突裁决界面、动态检索、版本/差异回退、前端规则界面在后续切片。
