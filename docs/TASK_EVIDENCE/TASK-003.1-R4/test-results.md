# 测试与构建结果 — TASK-003.1-R4

## 后端 pytest

- 命令：`.venv\Scripts\python.exe -m pytest -q`（在 `backend/` 目录）。
- 结果：**63 passed, 1 warning in 2.87s**。
- 较 R3 的 62 passed 新增 1 例：`test_ui_parser_reads_loader_and_lora_widget_values`。
- 唯一警告为既有遗留 `StarletteDeprecationWarning`（httpx / starlette.testclient），非本轮引入。
- 原始输出见 `pytest-output.txt`。

## 前端构建

- 命令：`npm run build`（在 `frontend/` 目录），执行 `tsc -b && vite build`。
- 结果：exit 0；33 modules transformed；`dist/index.html`、`dist/assets/index-*.css`、`dist/assets/index-*.js` 生成成功，✓ built in 534ms。
- 原始输出见 `frontend-build.txt`。

## 真机闭环（浏览器）

- 工作台 `http://127.0.0.1:17890` 打开，本地服务已连接（Python 3.13.18）。
- 两份样本经 API 导入并在浏览器工作流工作区打开，识别结果与报告一致：
  - `screenshots/suyuexisdxl-recognized.png`：Checkpoint / LoRA / 强度明细。
  - `screenshots/suyuexisdxl-prompt-nodes.png`：节点 5 负向、节点 4 正向。
  - `screenshots/silver-hair-recognized.png`：Checkpoint `RH_Illustrious_2.5D_V1`，无 LoRA。
  - `screenshots/services-online.png`：Ollama、ComfyUI 在线。

## 未覆盖项

- UI 样本的白名单确认 / 写入工作副本链路：按设计不开放，未在真机尝试。
- API workflow 真机写入闭环：仍缺一份 ComfyUI 「导出 API 格式」样本，留待后续。
