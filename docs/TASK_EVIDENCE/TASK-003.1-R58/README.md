# TASK-003.1-R58 阶段真机验收证据（R49–R57）

## 范围

R49–R57 批量切片后的阶段收口真机只读验收。本切片无代码改动，仅验收与归档。

## 环境与身份

- 后端由 `scripts/workbench_launcher.py` 以项目 `.venv` Python 3.13.18 启动，绑定
  `127.0.0.1:17890`，`WORKBENCH_OPEN_BROWSER=0`。
- 回收前核对进程身份：PID 13052（父）+ 20360（子），命令行
  `python -m uvicorn main:app --host 127.0.0.1 --port 17890`，可执行路径与工作目录均为本项目
  `.venv` 与 `backend/`；身份一致后终止，端口关闭，`.workbench.pid` / `.workbench-runtime.json`
  已清理。Ollama / ComfyUI 外部进程未触碰。

## 只读核对结果

- `GET /api/health` 200：`app=ComfyUI-Prompt-Workbench`，`version=0.1.0-dev.5`，
  Python 3.13.18。
- `GET /api/services/status`：Ollama 在线 `127.0.0.1:11434`，ComfyUI 在线 `127.0.0.1:8188`。
- `GET /api/models/catalog`：Checkpoint 13、LoRA 3。
- 数据库计数：`workbench_rule=0`、`generation_history=0`、`comfy_task=0`；profiles 13、
  model_identities 16、workflows 22（22 个为历次验收旧副本，既有 backlog，本次未新增、未批量删）。
- `GET /api/diagnostics` 200，`database_error=None`。

## 界面走查（截图见 `screenshots/`）

- 设置页：本地服务已连接；Ollama / ComfyUI 在线；存储目录检查齐全；操作区在位
  「保存设置」「导出诊断报告」（R52）「导出设置」（R55）。
- 工作流工作区：打开 `r31-compare.json`（已确认白名单），详情面板「历史版本（只读）」小节
  显示版本时间 `2026-11-18 07:54:10` 与正向 / 负向 Prompt 摘要；无恢复 / 差异按钮（R54）。
- 生成历史：空态展示「暂无生成历史。」；「网格视图」（R53）与「导出 JSON」（R51）在 0 条时
  禁用，「刷新」可用；版本号 `0.1.0-dev.5`。
- 页签记忆（R57）：停在「生成历史」刷新后仍回到历史页签，localStorage 偏好生效。

## 回归

- 后端：**224 passed, 1 warning**（`pytest-output.txt`）。
- 前端：`tsc -b && vite build` 绿，`index-BPnE4yPu.js 177.34 kB gzip 56.38 kB`
  （`frontend-build.txt`）。

## 收尾与边界

- 验收未提交任务、未登记规则、未导入新工作流副本；DB 三表归零。
- 历史筛选（状态 / 工作流 / 关键词 / 日期范围）在空态不渲染筛选控件，有记录时本地即时过滤；
  本次无历史记录，筛选交互以单测与构建兜底。
- 22 个历次验收旧工作流副本仍在 `userdata/workflows`，留待确认后批量清理。
