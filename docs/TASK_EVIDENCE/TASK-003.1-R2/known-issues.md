# 已知问题 — TASK-003.1-R2

## 1. 真机导入/写入闭环未完成（阻塞真机验收）

本机与仓库内没有真实 ComfyUI API workflow JSON 样本，以下任务书第五节步骤未在浏览器闭环：

- 导入真实 API workflow；正/负向 Prompt 节点识别；模型与 LoRA 节点识别；
- 手动调整节点角色；确认白名单后编辑 Prompt；写入工作副本；重开后持久化；
- 原始 workflow 未被修改；工作副本仅白名单 `inputs.text` 变化；`versions/` 快照为写入前版本；
- 导入 UI workflow 只读、写入按钮不可用。

对应服务端逻辑由后端既有 pytest 覆盖（57 passed），但不等同于真机验收。需提供一份真实 API workflow 样本后在浏览器补验。

## 2. 新增回归测试未补齐

任务书第三节列出 12 类回归测试，本轮 ChatGPT 仅提供 `workflow_service.py` 修正版、未提供测试文件内容。按分工豆包未自行编写测试断言。既有测试未覆盖、待补充的条目：

- 带 `nodes` 字典的兼容 API 结构识别（代码已支持，无显式用例）；
- 版本快照保存旧 Prompt 的显式断言；
- 重复导入 / 重开工作流的持久化断言。

## 3. 遗留 warning

后端 pytest 存在 `StarletteDeprecationWarning`（httpx + starlette.testclient 弃用提示），来自 FastAPI TestClient，非本轮改动引入，不影响测试结果。

## 4. 未决事项

- 等待 ChatGPT 基于 R2 回执与测试结果继续核查；如服务端逻辑仍有问题，由 ChatGPT 提供下一版修正。
- 真机验收与上述测试补齐完成前，工作流功能不视为最终验收通过。
