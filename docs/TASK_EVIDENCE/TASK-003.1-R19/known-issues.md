# R19 已知问题与 backlog

## 本轮遗留

- **带备注数值仍回退原文**：如 Scheduler `Karras（Euler A 时）`，备注未剥离，structured=None，比对归 unknown。
- **比对字段有限**：仅 Steps/CFG/Clip Skip/Sampler/Scheduler；Resolution 规则与实际 latent 尺寸未对接；VAE/CLIP 参数未纳入。
- **只取首个采样器组**：多采样器/自定义节点工作流未逐组比对。
- **比对只读**：不回写工作流、不触发 LLM、不生成修正建议；前端比对展示界面未实现。

## 既有 backlog（沿用，不在本轮处理）

- 架构标签归一化/同义归并；指纹规范化偏严格；模型节点清单硬编码；并发写锁未加。
- 前端 `**{filename}**` 星号纯文本未渲染；StarletteDeprecationWarning 遗留；Python 3.12 兼容性未验证。
- stopper 身份校验缺陷未修；LoRA 规则组合、冲突人工裁决界面、动态检索、global 规则来源未实现。
- VAE/CLIP 目录未进身份库索引；文件移动后按身份重新定位；全量/定时哈希策略与前端入口未实现。
