# local-source-snapshot — TASK-003.1 本机未提交源码快照

> 用途：在 ChatGPT 完成源码审查、提供正式修正版之前，把本机实际落盘的 TASK-003.1 功能源码原样归档，供审查对照。
> 本快照**不代表功能已验收或已修复**；后端仍有 6 项 API workflow 测试失败（见上级目录 `known-issues.md`、`pytest-output.txt`）。

## 归档口径

- 全部文件由本机实际工作区文件字节级复制，未改写、未格式化、未修复、未删减。
- 保留原文件编码与完整内容；复制后已逐文件做 SHA256 与源文件比对，结果一致（`ALL_MATCH: True`）。
- 未复制 `.venv`、`node_modules`、`userdata/`、模型、图片或任何运行数据。
- 路由注册相关源码片段即 `backend/main.py`（`workflow_router` 导入与 `include_router`），已包含在快照中；无其他独立路由配置文件。

## 文件清单

| 原始路径 | 归档文件名 | 字节数 | SHA256 |
| --- | --- | --- | --- |
| `backend/workflow_service.py` | `workflow_service.py` | 24234 | `3c8bdb666591d0f975eed71cdc6722963dcb5c57ca56faf29d62e86320640f29` |
| `backend/workflow_api.py` | `workflow_api.py` | 2400 | `4bc90e1dd93bb91064e8a451743fd11a8ec6ce7c26f042c47c041f6b5b1fb8f8` |
| `backend/test_workflow_service.py` | `test_workflow_service.py` | 7130 | `77cd367ba403cc31cf99018d557325cb4e3f92c67c4d0cc9712b4a30ebcef99b` |
| `frontend/src/WorkflowWorkbench.tsx` | `WorkflowWorkbench.tsx` | 14616 | `411a51da36efdbe1a2d01c8f72210f865ccf470eee0d9abab71852449b5f12e3` |
| `backend/main.py` | `main.py` | 19933 | `b6ee96651f9b6e525ced4e7266bd2dd81eb77318add1e9faae25c94671e3f335` |
| `frontend/src/App.tsx` | `App.tsx` | 11023 | `e57ea45e53efa3b0d77d86233fcef56d756a2f094a05fa9f971ee0ffb9673c0a` |
| `frontend/src/styles.css` | `styles.css` | 5966 | `68ff137113cff6cc4132ef2e2e2d09f6a3b321f54989c7a279532c782ab4ca37` |
| `backend/requirements.txt` | `requirements.txt` | 78 | `c651ae09709d90adc9fe5756d76c3c1fe0dace69c1e4fa3f0e3deb19f5c61c17` |
| `backend/datadir.py` | `datadir.py` | 16825 | `58a72ef8fad3b43e090eca00b5d0eb48fa11c207ee4a58085d8f12c5bc8baae1` |

归档时间（UTC）：2026-11-17T15:58:25.544933+00:00。

## 备注

- `backend/requirements-dev.txt` 仅引用 `requirements.txt` 并声明 `pytest>=8.3,<9`，未单独复制；如审查需要可从仓库 `backend/` 读取。
- 快照中的 `main.py` / `App.tsx` / `styles.css` 是本机工作区当前版本（含 TASK-003.1 接入改动，尚未提交）。
