# 测试与构建结果 — TASK-003.1-R6

## 后端 pytest

- 命令：`.venv\Scripts\python.exe -m pytest -q`（在 `backend/` 目录）。
- 结果：**69 passed, 1 warning in 3.75s**。
- 较 R5 的 64 passed 新增 5 例（`backend/test_model_catalog.py`）：
  - `test_catalog_extracts_checkpoint_lora_and_vae_options`
  - `test_catalog_marks_on_disk_only_when_directory_configured`
  - `test_catalog_unreachable_comfyui_reports_offline`
  - `test_catalog_endpoint_requires_session`
  - `test_catalog_endpoint_returns_injected_catalog`
- 唯一警告为既有遗留 `StarletteDeprecationWarning`（httpx / starlette.testclient），非本轮引入。
- 原始输出见 `pytest-output.txt`。

## 前端构建

- 命令：`npm run build`（在 `frontend/` 目录），执行 `tsc -b && vite build`。
- 结果：exit 0；33 modules transformed；`✓ built in 556ms`；产物 JS 156.65 kB / gzip 50.66 kB，CSS 5.44 kB / gzip 1.70 kB。
- 原始输出见 `frontend-build.txt`。

## 真机闭环（浏览器，127.0.0.1:17890）

| 验收项 | 结果 | 证据 |
| --- | --- | --- |
| 清单接口在线拉取 | 通过 | online=true；checkpoints 13、clips 0、vaes 3、loras 3 |
| 分组正确（VAE 不混入 Checkpoint） | 通过 | `samples/catalog-summary.json`：Checkpoint 13、VAE 3、LoRA 3 |
| 配置真实目录后存在性核对 | 通过 | 13 checkpoint、3 LoRA 全部 `on_disk=true` |
| 未配置目录时不臆测 | 通过 | 未配置目录项 `on_disk=null`，界面显示「目录未配置」 |
| 设置恢复原状 | 通过 | 核对后 `storage.checkpoint` / `storage.lora` 恢复为空串 |
| 浏览器页面渲染 | 通过 | `screenshots/model-catalog.png`、`model-catalog-list.png` |
| 未授权访问拦截 | 通过 | 未带会话访问 `/api/models/catalog` 返回 401（离线测试覆盖） |

## 未覆盖项

- 模型文件 SHA256 身份记录、规则继承/冲突检测、动态检索未做，属后续 M3 切片。
- Ollama 候选生成与结构化验证未做，属 M4。
- 真实出图端到端（提交 ComfyUI 任务、进度、结果回显、输出目录索引）未做，属 M6。
