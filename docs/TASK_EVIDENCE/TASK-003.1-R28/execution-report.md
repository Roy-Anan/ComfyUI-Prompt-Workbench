# R28 执行报告

## 1. 背景

规则库经 R10/R14 已可持久化与导入，但前端只能在工作流比对面板间接看到结论，规则记录本身不可见。本切片在设置页提供只读清单，便于核对已入库规则的层级、作用域、值、来源与可信度。

## 2. 实施步骤

1. `App.tsx` 新增 `RuleRecord` 类型与层级/来源/可信度中文标签映射；`refresh()` 并行拉取 `/api/rules`。
2. 规则面板按 checkpoint / architecture / global 顺序分组，每条展示规则键、作用域、原始值、结构化摘要（有则显示）、备注，以及来源、可信度、版本标签。
3. 空库显示「规则库为空」；面板不提供任何写操作控件。
4. `styles.css` 补分组标题、条目行与标签样式。

## 3. 真机核对

- 前置：导入 `ponyDiffusionV6XL_v6.safetensors` 档案 20 条，0 拒绝。
- 规则分布：checkpoint 15、architecture 5、global 0。
- 浏览器打开服务与设置页，规则库面板：模型档案（15）逐条展示；架构基线（5）含 Base Architecture、Clip Skip、Model Type、Trigger Words、VAE；来源/可信度/版本标签与后端记录一致。
- 载荷：`samples/rules-payload.json`；截图 `screenshots/rules-checkpoint-group.png`、`rules-architecture-group.png`。
- 清理后规则表 0 条。

## 4. 进程与数据

- 验收后回收后端进程，17890 释放；Ollama / ComfyUI 未触碰。
- userdata 工作流副本与真机库为运行时产物，未入库；规则表已归零。

## 5. 未做

- 规则候选勾选/驳回、人工编辑、删除与档案审核导入的前端入口；冲突人工处理界面为后续切片。
