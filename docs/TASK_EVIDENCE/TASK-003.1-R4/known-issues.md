# 已知问题 — TASK-003.1-R4

## 1. API workflow 真机写入闭环仍未完成（沿用 R3 遗留）

两份真机样本均为 UI 界面格式，按设计只支持只读解析。以下链路仍需一份 ComfyUI「导出 API 格式」样本后补验：

- 导入真实 API workflow；确认正/负向白名单；编辑 Prompt；写入工作副本；重开持久化；
- 原始文件未被修改；工作副本仅白名单 `inputs.text` 变化；`versions/` 快照为写入前版本。

服务端白名单 / 完整性校验由 pytest 覆盖（63 passed），不等同真机验收。

## 2. Ollama 对话与 ComfyUI 任务对接尚未实现（M4 / M6 范围）

本轮 `/api/services/status` 仅做连通性探测：

- 未实现 Ollama 模型选择、参数配置、候选生成与结构化验证（M4）。
- 未实现 ComfyUI HTTP 提交、队列、WebSocket 进度、结果拉取与输出目录映射（M6）。
- 工作台未内置启停 Ollama / ComfyUI 进程的能力；本轮服务由本次验收手动拉起，遵循「工作台只连接和管理任务，不擅自控制外部进程」的既有口径。

## 3. 外部模型 / 输出目录未在设置页对接

- `storage.checkpoint`、`storage.lora` 当前为空串；真机模型清单来自 ComfyUI `object_info`，未做本机目录扫描与身份缓存（M3 / M8）。
- ComfyUI 输出目录 `ComfyUI\output` 尚未在工作台登记或在历史中索引（M7）。

## 4. 其他 backlog（沿用既有清单）

- 指纹规范化偏严格：数字 `1`/`1.0`、浮点精度、空值空串、链接 slot 序号等等价表示可能被误判；涉及安全口径，未放宽。
- 模型节点清单硬编码，可抽为规则配置；并发写锁未加（单用户本机场景）。
- 前端 `**{filename}**` 星号纯文本未做 Markdown 渲染（展示问题，不影响安全）。
- `StarletteDeprecationWarning` 为既有遗留警告；Python 3.12 兼容性未验证；显存阈值待真机测量。

## 5. 未决事项

- 等待一份真实 API workflow 样本，完成 M1/M2 真机闭环；之后再按 ROADMAP 进入 M3。
