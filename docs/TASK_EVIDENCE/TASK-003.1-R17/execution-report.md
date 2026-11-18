# R17 执行报告

## 目标

把当前工作流识别出的 checkpoint 文件名与规则库精确匹配，按 checkpoint → architecture → global 三级上下文只回传相关规则；落实「只将当前工作流相关规则传给 LLM」「规则继承优先级由程序确定」「冲突和未知不由 LLM 猜测」。

## 改动

### 后端

- `rule_store.py`
  - `context_for_checkpoint(connection, checkpoint)`：返回 `{status, checkpoint, architecture, checkpoint_rules, architecture_rules, global_rules}`；只归集本上下文相关规则，无关 checkpoint 规则不外泄。
  - `_checkpoint_architecture(records, checkpoint)`：先在 checkpoint 桶找 Base Architecture 记录；找不到再回退 architecture 桶同键记录；与架构 scope 做相等/前缀/包含匹配。
- `workflow_api.py`
  - `_database_path()`：`datadir.database_path(default_data_root())`。
  - `_checkpoint_filename(report)`：取 `ckpt_name`/`unet_name`。
  - `GET /api/workflows/{workflow_id}/rules`：无识别 checkpoint 返回 `unregistered` + `reason=no_checkpoint_recognized`；有文件名则走 `context_for_checkpoint`。
- `test_workflow_rules.py`：3 例。

## 真机过程

1. 首跑发现架构规则 0 条、arch=None。排查：Base Architecture 事实在 R16 已被重定向到架构级落库，checkpoint 桶无该记录，关联失败；`_checkpoint_architecture` 增加架构桶回退查找。
2. 首跑清理脚本只删上下文返回的桶，漏删架构桶 2 条残留；改为拉全量规则后逐条删除。
3. 重启后端重跑：registered，checkpoint=intorealismUltra_v80.safetensors，arch=SDXL 1.0，14 checkpoint + 2 architecture；ghost_missing.safetensors 返回 unregistered；清理后 rules=0。

## 结论

切片目标达成；上下文归集正确，未登记模型如实标记，无规则臆造。
