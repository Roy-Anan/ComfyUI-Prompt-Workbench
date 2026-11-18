# 已知问题 — TASK-003.1-R5

## 1. 出图端到端未对接（M6 范围）

工作台已能在工作副本内安全编辑 Prompt，但尚未：

- 把工作副本提交到 ComfyUI `/prompt`；
- 跟踪队列与 WebSocket 进度；
- 拉取生成历史与图片结果；
- 登记 / 索引 ComfyUI 输出目录 `ComfyUI\output`。

本轮真机只验证到「写入工作副本 + 完整性校验 + 持久化」，未触发出图。

## 2. Ollama 对话生成未实现（M4 范围）

- 后端仅有 `/api/services/status` 连通性探测；模型选择、参数配置、候选 Prompt 生成与结构化验证均未做。

## 3. 外部模型目录与身份缓存未对接（M3 / M8）

- `storage.checkpoint`、`storage.lora` 仍为空串；真机模型清单来自 ComfyUI `object_info`，未做本机目录扫描与身份缓存。

## 4. 既有 backlog（沿用）

- 指纹规范化偏严格：数字 `1`/`1.0`、浮点精度、空值空串、链接 slot 序号等等价表示可能被误判；涉及安全口径，未放宽。
- 模型节点清单硬编码，可抽为规则配置；并发写锁未加（单用户本机场景）。
- 前端 `**{filename}**` 星号纯文本未做 Markdown 渲染（展示问题，不影响安全）。
- `StarletteDeprecationWarning` 为既有遗留警告；Python 3.12 兼容性未验证；显存阈值待真机测量。

## 5. 远端推送状态

- R4 提交 `52d8d3a` 与本轮 R5 改动在网络恢复后需一并 `git push origin dev`；GitHub 直连在本机当前网络下被重置/超时，本地提交与证据均已落盘。
