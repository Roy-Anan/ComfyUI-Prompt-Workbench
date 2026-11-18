# TASK-003.1-R52 证据汇总（轻量化归档）

## 范围

M9 数据维护：用户主动生成的只读本地诊断报告。批量终验节奏，真机验收在阶段收口统一进行。

## 改动

- 后端 `main.py`：新增 `GET /api/diagnostics`，汇总应用/版本、Python/平台、数据域计数（规则、
  历史、任务、模型身份、工作流、档案）、托管与外部存储目录存在性、本地 Ollama/ComfyUI 可达性；
  数据库异常记入 `database_error` 而不中断报告；`uploaded: false`，不含模型权重、原图或完整
  Prompt 载荷。
- 前端 `App.tsx`：设置页加「导出诊断报告」按钮，Blob 下载本地 JSON，默认不上传。
- 文档：`docs/ROADMAP.md` R52 段、`PROJECT_STATE.md` 第 62 节。

## 测试结果

- 后端：**221 passed, 1 warning**（`pytest-output.txt`）。
- 前端：`tsc -b && vite build` 绿，`index-BCj7cW2p.js 175.03 kB gzip 55.81 kB`（`frontend-build.txt`）。

## 边界 / backlog

- 备份/恢复、数据库迁移、崩溃恢复与完整性检查、手动更新检查留后续切片。
