# Doubao-Receipt — TASK-003.1-R1 豆包原始回执

> 任务性质：**只归档本机未提交源码供 ChatGPT 审查，未修复 TASK-003.1、未改功能实现、未修测试。**
> 归档时间：2026-11-17（UTC 见快照 MANIFEST）。
> 本文件保留完整原始回执；提交 SHA、推送结果、最终工作区状态在提交推送后回填。

## 1. 任务目的

TASK-003.1 功能代码已在本机落盘，后端 6 项测试失败、尚未提交。ChatGPT 已确认修复方向为适配 ComfyUI 标准扁平 API workflow 格式。在 ChatGPT 完成源码审查并提供修正版之前，本任务只把本机实际源码原样归档到 GitHub，不自行修改功能实现。

## 2. 开始前核对

- 仓库：`D:\AI\ComfyUI-Prompt-Workbench-Git`
- 当前分支：`dev`
- 执行前重新核对远端 dev：`4066c9b48af527a1b7a87f4d0c207686ffc19ffd`（本地 HEAD 与 origin/dev 一致）
- origin/main：`3084866aa85595133c7a1179b15ddd71e659d8f3`
- 工作区开始状态：保留本机未提交功能代码，未覆盖、未重置、未清理。

### 本地未提交文件清单（开始时）

| 文件 | 状态 |
| --- | --- |
| `backend/main.py` | 已修改（未暂存） |
| `frontend/src/App.tsx` | 已修改（未暂存） |
| `frontend/src/styles.css` | 已修改（未暂存） |
| `backend/workflow_service.py` | 未跟踪 |
| `backend/workflow_api.py` | 未跟踪 |
| `backend/test_workflow_service.py` | 未跟踪 |
| `frontend/src/WorkflowWorkbench.tsx` | 未跟踪 |

## 3. 归档文件完整清单与 SHA256

归档目录：`docs/TASK_EVIDENCE/TASK-003.1/local-source-snapshot/`
全部由本机实际文件字节级复制，复制后逐文件 SHA256 与源文件比对一致（`ALL_MATCH: True`）。

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

另归档：`local-source-snapshot/README.md`、`local-source-snapshot/MANIFEST.md`（清单与校验信息，非源码）。

### 路由注册相关源码说明

路由注册只出现在 `backend/main.py`（`from workflow_api import router as workflow_router` 与 `app.include_router(workflow_router)`），已包含在快照中；本机无其他独立路由配置文件。`backend/requirements-dev.txt` 仅引用 `requirements.txt` 并声明 `pytest>=8.3,<9`，未单独复制。

## 4. 保留的原始失败证据（未修改）

位于 `docs/TASK_EVIDENCE/TASK-003.1/`，本次未改动：

- `Doubao-Receipt.md`
- `pytest-output.txt`
- `frontend-build.txt`
- `known-issues.md`
- `README.md`

## 5. 禁止事项执行情况

- 未修改任何功能源码。
- 未修复测试、未改测试断言绕过失败、未把 API 样本改成 `nodes` 包裹格式、未删除失败测试。
- 未升级依赖。
- 未修改 `main`。
- 未提交 `userdata/`、`frontend/dist/`、虚拟环境或模型文件。

## 6. Git diff --stat 与提交文件列表

> 提交前工作区中既有功能源码的未提交改动（不随本次入库）：

```text
 backend/main.py         |   5 +-
 frontend/src/App.tsx    |  23 +++++++++
 frontend/src/styles.css | 125 ++++++++++++++++++++++++++++++++++++++++++++++++
 3 files changed, 152 insertions(+), 1 deletion(-)
```

本次实际提交文件列表（12 个，3439 行新增，仅证据归档）：

```text
 docs/TASK_EVIDENCE/TASK-003.1-R1/Doubao-Receipt.md
 docs/TASK_EVIDENCE/TASK-003.1/local-source-snapshot/App.tsx
 docs/TASK_EVIDENCE/TASK-003.1/local-source-snapshot/MANIFEST.md
 docs/TASK_EVIDENCE/TASK-003.1/local-source-snapshot/README.md
 docs/TASK_EVIDENCE/TASK-003.1/local-source-snapshot/WorkflowWorkbench.tsx
 docs/TASK_EVIDENCE/TASK-003.1/local-source-snapshot/datadir.py
 docs/TASK_EVIDENCE/TASK-003.1/local-source-snapshot/main.py
 docs/TASK_EVIDENCE/TASK-003.1/local-source-snapshot/requirements.txt
 docs/TASK_EVIDENCE/TASK-003.1/local-source-snapshot/styles.css
 docs/TASK_EVIDENCE/TASK-003.1/local-source-snapshot/test_workflow_service.py
 docs/TASK_EVIDENCE/TASK-003.1/local-source-snapshot/workflow_api.py
 docs/TASK_EVIDENCE/TASK-003.1/local-source-snapshot/workflow_service.py
```

## 7. 提交 SHA 与推送结果

- 提交 SHA：`73b71a958302ca08b28f2b77b94ba546e03fe2f3`
- 提交信息：`docs(evidence): archive TASK-003.1 local source snapshot`
- 提交身份：Roy-Anan `<1538072315@qq.com>`
- 推送结果：成功，`4066c9b..73b71a9  dev -> dev`（push exit 0）；回读本地 HEAD 与 origin/dev 一致于 `73b71a9`。

## 8. dev 与 main SHA

- dev 起始：`4066c9b48af527a1b7a87f4d0c207686ffc19ffd`
- dev 最终：`73b71a958302ca08b28f2b77b94ba546e03fe2f3`
- main：`3084866aa85595133c7a1179b15ddd71e659d8f3`（本地 / origin/main 一致，未修改）

## 9. 工作区状态

提交后工作区（未入库功能源码，保留在本地）：

```text
## dev...origin/dev
 M backend/main.py
 M frontend/src/App.tsx
 M frontend/src/styles.css
?? backend/test_workflow_service.py
?? backend/workflow_api.py
?? backend/workflow_service.py
?? frontend/src/WorkflowWorkbench.tsx
```

功能源码仍保留在本地工作区未入库，等待 ChatGPT 审查后提供正式修正版。`userdata/`、`frontend/dist/` 未被跟踪。

## 10. 完整执行过程与异常

1. 拉取远端 dev 并核对本地/远端一致于 `4066c9b`，main 未变。
2. 盘点 9 个待归档文件，全部存在；确认 `requirements.txt`、`datadir.py` 在位；`requirements-dev.txt` 仅为引用，未复制。
3. 脚本字节级复制到 `local-source-snapshot/`，计算大小与 SHA256，生成 `MANIFEST.md`。
4. 校验脚本逐文件比对快照与源文件哈希，`ALL_MATCH: True`。
5. 确认原始失败证据 4 份在位且未改动。
6. 写快照 README 与本回执；暂存仅证据归档文件，功能源码保持未暂存。
7. 提交并推送 dev；回读核对本地/远端同步、main 未变、userdata/dist 未跟踪。

异常：无。未执行测试、未启动服务、未做真机验收（本任务不要求）。

## 11. 未解决事项

- TASK-003.1 的 6 项 API workflow 测试失败仍未修复，阻塞问题见 `docs/TASK_EVIDENCE/TASK-003.1/known-issues.md`（P1：解析器与扁平 API prompt 结构口径不一致）。
- 本任务不宣布 TASK-003.1 已修复；等待 ChatGPT 审查快照后提供正式修正版。
