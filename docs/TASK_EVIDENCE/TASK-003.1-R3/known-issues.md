# 已知问题 — TASK-003.1-R3

## 1. 真机导入/写入闭环仍未完成（阻塞真机验收）

本机与仓库内仍无真实 ComfyUI API workflow JSON 样本，以下链路未在浏览器闭环：

- 导入真实 API workflow；正/负向 Prompt、模型与 LoRA 节点识别；
- 手动调整节点角色；确认白名单后编辑 Prompt；写入工作副本；重开后持久化；
- 原始 workflow 未被修改；工作副本仅白名单 `inputs.text` 变化；`versions/` 快照为写入前版本；
- 导入 UI workflow 只读、写入按钮不可用。

服务端逻辑由本轮 pytest（62 passed）覆盖，但不等同于真机验收。需提供一份真实 API workflow 样本后在浏览器补验。

## 2. 指纹规范化偏严格（backlog，本轮未放宽）

`fingerprint` 基于 `json.dumps(..., sort_keys=True)` 的字节哈希，以下等价表示可能被误判为不同：

- 数字 `1` 与 `1.0`；浮点精度差异；
- 空串与空值；链接 slot 序号差异；
- 键顺序之外的空白/格式差异（`sort_keys` 已消除键序影响）。

该项放宽涉及安全口径，需在真实样本上确认后再改，本轮刻意保持原强度。

## 3. 其他 backlog

- 工程分层：模型节点硬编码清单可抽为规则配置；并发写锁未加（当前单用户本机场景）。
- 前端 `**{filename}**` 星号纯文本未做 Markdown 渲染（展示问题，不影响安全）。
- 后端 `StarletteDeprecationWarning` 为既有遗留警告，非本轮引入。
- Python 3.12 兼容性未验证；显存阈值待真机测量。

## 4. 未决事项

- 等待真实 ComfyUI 导出样本，完成 M1/M2 真机闭环后再进入 M3。
