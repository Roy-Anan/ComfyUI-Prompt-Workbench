# 测试与构建结果 — TASK-003.1-R5

## 后端 pytest

- 命令：`.venv\Scripts\python.exe -m pytest -q`（在 `backend/` 目录）。
- 结果：**64 passed, 1 warning in 2.68s**。
- 较 R4 的 63 passed 新增 1 例：`test_real_exported_api_workflow_full_writeback_roundtrip`。
- 唯一警告为既有遗留 `StarletteDeprecationWarning`（httpx / starlette.testclient），非本轮引入。
- 原始输出见 `pytest-output.txt`。

## 前端构建

- 命令：`npm run build`（在 `frontend/` 目录），执行 `tsc -b && vite build`。
- 结果：exit 0；33 modules transformed；`✓ built in 517ms`。
- 原始输出见 `frontend-build.txt`。

## 真机闭环（浏览器，127.0.0.1:17890）

| 验收项 | 结果 | 证据 |
| --- | --- | --- |
| API 样本导入识别 | 通过 | `screenshots/api-recognized.png`：API · 8 节点，Checkpoint / LoRA / 强度正确 |
| 白名单确认 | 通过 | 节点 4 正向、节点 5 负向；状态「已确认白名单」 |
| 写回工作副本并校验 | 通过 | `screenshots/api-writeback.png`：1 个节点变化，完整性校验通过 |
| 刷新重开持久化 | 通过 | `screenshots/api-reopen-persisted.png`：重开后标记仍在 |
| 原始文件未改 | 通过 | 文件系统核对：`original.json` 无验收标记，负向两版一致 |
| 写入前快照 | 通过 | `versions/` 1 份快照，内容与原始一致 |
| 非白名单篡改防护 | 通过 | 离线脚本改 seed 后写入被拒（WorkflowError） |

## 未覆盖项

- 真实出图端到端（提交 ComfyUI 任务、进度、结果回显、输出目录索引）未做，属 M6。
- Ollama 候选生成与结构化验证未做，属 M4。
