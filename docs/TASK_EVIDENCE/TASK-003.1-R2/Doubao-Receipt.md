# Doubao-Receipt — TASK-003.1-R2 豆包完整原始回执

> 分工口径：代码由 ChatGPT 提供，豆包只按原文落盘、跑测、实机验证、归档证据、做 Git 操作；不自行设计或重写核心实现，不擅自加功能/改架构。
> 本回执保留完整原始执行记录；提交 SHA、推送结果、最终工作区状态在提交推送后回填。

## 1. 任务目标

根据 ChatGPT 提供的完整 `backend/workflow_service.py` 修正版，修复 TASK-003.1 的工作流解析与 Prompt 白名单写入。本轮不修复测试、不改测试断言、不把扁平 API 样本改成 `nodes` 包裹格式、不删失败测试、不升级依赖、不改 main、不合并分支。

## 2. 开始前核对

- 仓库：`D:\AI\ComfyUI-Prompt-Workbench-Git`，分支 `dev`。
- 拉取远端后核对：本地 HEAD = origin/dev = `bd36c7eae7fd5840c72e090b6ac58bd1c098a2bc`。
- origin/main = `3084866aa85595133c7a1179b15ddd71e659d8f3`（未修改）。
- 既有 TASK-003.1 本地未提交功能文件仍在位，未重置、未清理、未覆盖。

开始时工作区：

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

## 3. 现状审查（落盘前）

- `backend/main.py`：第 22 行 `from workflow_api import router as workflow_router`，第 233 行 `app.include_router(workflow_router)`，路由已注册。
- 全局会话中间件（`require_session`）覆盖所有 `/api` 路径；浏览器 cookie 会话的状态变更请求走 CSRF 校验（`X-Workbench-CSRF`）。工作流路由受现有认证与 CSRF 保护，未重复改造认证架构。
- `backend/workflow_api.py`：`WorkflowStore(datadir.default_data_root() / "workflows")`；接口为 `GET /api/workflows`、`POST /api/workflows/import`、`GET /api/workflows/{id}`、`POST /api/workflows/{id}/confirm`、`POST /api/workflows/{id}/write`。
- 未发现导入错误、路由错误或 API 客户端不兼容。

## 4. 实际修改文件

| 文件 | 处理 |
| --- | --- |
| `backend/workflow_service.py` | 完整替换为 ChatGPT 本轮提供的修正版（原文落盘，未删减、未改实现）。落盘前旧版备份到会话临时目录，不入库。 |
| `backend/workflow_api.py` | 保留本机版本，未重写。 |
| `backend/test_workflow_service.py` | 保留本机版本，未删测试、未降断言。 |
| `frontend/src/WorkflowWorkbench.tsx` | 保留本机版本，未重写。 |
| `backend/main.py` | 保留本机接入改动，未改认证架构。 |
| `frontend/src/App.tsx` | 保留本机接入改动。 |
| `frontend/src/styles.css` | 保留本机接入改动。 |

修正版 `workflow_service.py` SHA256：`cfe4954bec31881d414829cab6d7fecde862ad8e71d25e7b871d73b99f82a9f3`，字节数 25689。

## 5. 测试命令与完整结果

### 后端 pytest

命令（项目 `.venv`，工作目录 `backend/`）：

```powershell
D:\AI\ComfyUI-Prompt-Workbench-Git\.venv\Scripts\python.exe -m pytest -q
```

原始输出：`pytest-output.txt`。

结果：**57 passed, 1 warning in 7.68s**（exit 0）。

```text
.........................................................                [100%]
============================== warnings summary ===============================
..\.venv\Lib\site-packages\fastapi\testclient.py:1
  StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
57 passed, 1 warning in 7.68s
```

- 既有 `test_main.py`、`test_scripts.py` 全过；`test_workflow_service.py` 全过。
- 上一轮 6 个 API 用例失败已消除。
- 唯一 warning 来自 FastAPI TestClient 的 httpx 弃用提示，非本轮改动引入。

### 语法编译

```powershell
python -m py_compile backend/workflow_service.py
```

exit 0。

### 前端构建

命令（工作目录 `frontend/`）：

```powershell
npm run build
```

原始输出：`frontend-build.txt`。结果：**exit 0**。

```text
> comfyui-prompt-workbench@0.1.0 build
> tsc -b && vite build

vite v5.4.21 building for production...
✓ 33 modules transformed.
dist/index.html                   0.41 kB │ gzip:  0.28 kB
dist/assets/index-BPFWm_Qr.css    4.64 kB │ gzip:  1.52 kB
dist/assets/index-C4-wWkSq.js   154.92 kB │ gzip: 50.28 kB
✓ built in 864ms
```

## 6. 回归测试覆盖口径

任务书第三节列出 12 类建议回归测试。本轮 ChatGPT 仅提供 `workflow_service.py` 修正版，未提供新增测试文件内容；按分工豆包未自行编写测试断言，沿用本机既有 `test_workflow_service.py`（11 个工作流用例）。

既有用例覆盖：扁平 API 识别、角色识别、写入仅改白名单文本、原始文件不变、非白名单变更拒绝、原始指纹变化拒绝、未确认拒绝、UI 只读、超 20MB 拒绝、无效格式拒绝。

既有测试未显式覆盖、待 ChatGPT 后续补充：

1. 带 `nodes` 字典的兼容 API 结构识别（代码已支持，无显式用例）。
2. 版本快照保存旧 Prompt 而非新 Prompt 的显式断言。
3. 重复导入 / 重开工作流的持久化断言。

未删除原有测试，未降低断言标准，未把扁平样本改成 `nodes` 包裹格式。

## 7. 真机验收逐步结果

环境：本地 Edge，`http://127.0.0.1:8000`；后端由项目 `.venv` uvicorn 启动，仅回环监听。

| # | 任务书步骤 | 真实结果 |
| --- | --- | --- |
| 1 | 启动工作台 | 成功；健康检查返回 `app=ComfyUI-Prompt-Workbench`、版本 `0.1.0-dev.5`、Python 3.13.18。 |
| 2 | 浏览器打开 8000 | 页面正常加载，标题 `ComfyUI Prompt Workbench`。 |
| 3 | 工作流页面可打开 | 「工作流工作区」页面渲染正常，空列表提示「还没有导入工作流」。 |
| 4 | 导入真实 ComfyUI API workflow JSON | **未完成**：本机与仓库无真实 API workflow 样本，未伪造样本。 |
| 5 | 正/负向 Prompt 节点识别正确 | 未在真机闭环；服务端逻辑由 pytest 覆盖。 |
| 6 | 模型加载节点与 LoRA 节点信息正确 | 未在真机闭环；服务端逻辑由 pytest 覆盖。 |
| 7 | 手动调整节点角色 | 未在真机闭环。 |
| 8 | 确认白名单后编辑 Prompt | 未在真机闭环。 |
| 9 | 写入工作副本 | 未在真机闭环。 |
| 10 | 重开后 Prompt 仍存在 | 未在真机闭环。 |
| 11 | 原始 workflow 文件未被修改 | 未在真机闭环；服务端由既有写入测试校验原始文件不变。 |
| 12 | 工作副本除白名单 `inputs.text` 外无其他字段变化 | 未在真机闭环；服务端由既有完整性校验测试覆盖。 |
| 13 | `versions/` 快照为写入前版本 | 未在真机闭环；代码保存写入前 `working`，待样本补验。 |
| 14 | 导入 UI workflow 只读、写入不可用 | 未在真机闭环；服务端 `safe_prompt_write_supported=False`，既有 UI 用例覆盖。 |
| 15 | ComfyUI 未被启动/关闭/重启 | 已确认：验收后无残留 uvicorn/ComfyUI 命令行进程。 |

补充：浏览器会话下 `GET /api/workflows` 返回 200 OK（空列表），工作流列表接口链路打通。截图 `screenshots/workflow-page-empty.png`；访问日志 `logs/r2-uvicorn.log`。

## 8. 原始文件 / 工作副本 / 版本快照校验

- 真机未导入样本，`userdata/workflows/` 验收后为空，未产生业务数据。
- 服务端校验（pytest 覆盖）：写入前工作副本除白名单 text 外必须与原始一致；写入后还原白名单文本必须得到原始工作流；原始文件指纹变化则拒绝写入；版本快照保存写入前的 `working.json`。
- 未在真机对真实样本复核上述项，结论以服务端测试为准，待样本补验。

## 9. Git diff 与提交文件清单

### 已跟踪文件未提交改动（diff --stat）

```text
 backend/main.py         |   5 +-
 frontend/src/App.tsx    |  23 +++++++++
 frontend/src/styles.css | 125 ++++++++++++++++++++++++++++++++++++++++++++++++
 3 files changed, 152 insertions(+), 1 deletion(-)
```

完整原始 diff：`git-diff-raw.txt`。

### 未跟踪功能文件（本轮随代码提交）

- `backend/workflow_service.py`（25689 字节，修正版）
- `backend/workflow_api.py`（2400 字节）
- `backend/test_workflow_service.py`（7130 字节）
- `frontend/src/WorkflowWorkbench.tsx`（14616 字节）

### 本轮证据新增

`docs/TASK_EVIDENCE/TASK-003.1-R2/`：`README.md`、`execution-report.md`、`environment-report.md`、`test-results.md`、`pytest-output.txt`、`frontend-build.txt`、`git-diff.md`、`git-diff-raw.txt`、`known-issues.md`、`screenshots/workflow-page-empty.png`、`logs/r2-uvicorn.log`、本回执。

## 10. dev / main SHA 与推送结果

- dev 起始：`bd36c7eae7fd5840c72e090b6ac58bd1c098a2bc`
- dev 最终：`bddc82c35de536978dd54f9d03716b9bb99962a7`
- main：`3084866aa85595133c7a1179b15ddd71e659d8f3`（本地 = origin/main，未修改）
- 提交信息：`fix(workflow): support API prompt format and safe writes`
- 提交身份：Roy-Anan `<1538072315@qq.com>`
- 提交规模：18 files changed, 2203 insertions(+), 1 deletion(-)
- 推送结果：成功，`bd36c7e..bddc82c  dev -> dev`（push exit 0）；回读本地 HEAD = origin/dev = `bddc82c`。

## 11. 工作区状态

提交后工作区干净：

```text
## dev...origin/dev
```

`userdata/`、`frontend/dist/` 未跟踪；未提交 ComfyUI 生成任务。所有本轮功能代码与 R2 证据已随 `bddc82c` 入库 dev。

## 12. 异常与处理

- 停止脚本首次因结构化运行记录缺少进程启动时间而 fail-closed，未杀进程；补齐真实 CreationDate 后二次执行成功停止 PID 15668（含子进程），端口 8000 释放，未误杀其他程序。
- 真机导入/写入闭环因缺少真实样本未完成，已在第 7 节逐项标注，不计为已验收。
- 本轮未执行 ComfyUI 任务，未安装或升级任何运行时。

## 13. 未决事项

- 需提供真实 ComfyUI API workflow JSON，在浏览器补验导入、角色识别、确认、写入、持久化、原始/工作副本/版本快照校验，以及 UI workflow 只读。
- 待 ChatGPT 补充三类回归测试（兼容 `nodes` 结构识别、版本快照旧文本断言、持久化断言）。
- 在上述补齐前，工作流功能不视为最终验收通过；本回执不声称 TASK-003.1 已完整交付。
