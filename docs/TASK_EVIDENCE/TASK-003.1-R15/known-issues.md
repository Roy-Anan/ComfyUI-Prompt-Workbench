# R15 已知问题与欠账

## 本轮未实现（留后续切片）

1. 结构化结果未接前端：规则清单/详情尚未展示 `structured`，也未用于参数比对、范围冲突检测。
2. 结构化覆盖有限：仅 Steps、CFG、Clip Skip、Resolution、Sampler、Scheduler；提示词标签、架构、VAE、触发词等散文字段不拆。
3. 带备注的数值（如 `2； 2（示例图元数据…）`、`2（非 V3 独立参数）`）当前回退原文、`structured=None`，未剥离备注后再解析。
4. architecture/global 级规则装载、逐候选勾选/驳回/差异预览、多模型/LoRA 规则组合、冲突人工裁决界面、动态检索、LLM 上下文装配、版本/差异回退仍未实现。

## 既有 backlog（沿用 R14）

- stopper 身份校验缺陷：运行记录 `creation_date=null`，根进程退出后身份校验失败，需手动核对 PID 命令行/父子关系/工作目录后回收。
- 指纹规范化偏严格；VAE/CLIP 目录未纳入身份库索引；目录不递归；并发写锁未加；全量/定时哈希策略与前端触发入口未做。
- 前端 `**{filename}**` 星号纯文本未渲染；StarletteDeprecationWarning 遗留。
