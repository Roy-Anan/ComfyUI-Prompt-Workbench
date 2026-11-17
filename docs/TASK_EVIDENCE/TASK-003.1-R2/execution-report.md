# 执行报告 — TASK-003.1-R2

## 任务目标

按 ChatGPT 提供的完整 `backend/workflow_service.py` 修正版修复 TASK-003.1 工作流功能。豆包只负责按原文落盘、测试、实机验证、证据归档与 Git 操作，不自行设计或重写核心逻辑。

## 实际修改文件

| 文件 | 处理 | 说明 |
| --- | --- | --- |
| `backend/workflow_service.py` | 完整替换为 ChatGPT 修正版 | 本轮唯一由修正版覆盖的源码；落盘前已备份旧版到会话临时目录（不入库）。SHA256 见回执。 |
| `backend/workflow_api.py` | 保留本机 TASK-003.1 版本 | 未重写；核对使用 `datadir.default_data_root()/"workflows"`，受全局 `/api` 会话与 CSRF 中间件保护。 |
| `backend/test_workflow_service.py` | 保留本机版本 | 未删测试、未降断言；本轮未新增测试（ChatGPT 未提供测试文件）。 |
| `frontend/src/WorkflowWorkbench.tsx` | 保留本机版本 | 未重写。 |
| `backend/main.py` | 保留本机接入改动 | 已核对第 22 行导入 `workflow_router`、第 233 行 `include_router(workflow_router)`；未改认证架构。 |
| `frontend/src/App.tsx` | 保留本机接入改动 | 已核对 `WorkflowWorkbench` 引入与工作流页面切换。 |
| `frontend/src/styles.css` | 保留本机接入改动 | 未重写。 |

## 修正版实现要点（按交付代码原文，非豆包设计）

- 同时识别 ComfyUI 标准扁平 API prompt 与带 `nodes` 的兼容包装结构；读、确认、写入流程统一走同一节点提取函数。
- 修复写入后错误地拿修改前副本比较的问题；写入前保存真正的旧版本快照。
- 写入后重新验证：还原白名单文本后必须与原始工作流完全一致。
- 导入中途失败时清理不完整目录。

## 真机验收记录（浏览器，本地 Edge，127.0.0.1:8000）

| 步骤 | 结果 |
| --- | --- |
| 启动工作台（uvicorn 回环 8000） | 成功，健康检查返回应用标识与版本 `0.1.0-dev.5`、Python 3.13.18。 |
| 浏览器打开 `http://127.0.0.1:8000` | 页面正常加载，标题 `ComfyUI Prompt Workbench`。 |
| 本地服务连接状态 | 绿点「已连接」，Python 3.13.18。 |
| 工作流页面可打开 | 「工作流工作区」页面渲染正常，提示「还没有导入工作流」。 |
| 工作流列表接口 | 浏览器会话下 `GET /api/workflows` 返回 200 OK（空列表），链路打通。 |
| 导入真实 API workflow | **未完成**：本机与仓库内无真实 ComfyUI API workflow JSON 样本，未伪造样本走真机闭环。 |
| 正/负向 Prompt 节点识别、模型/LoRA 节点、手动调整角色、确认白名单、编辑写入、重开持久化、原始文件未改、非白名单字段无变化、版本快照为旧版本、UI workflow 只读 | **未在真机闭环**；对应逻辑由后端 pytest 覆盖（既有用例），真机步骤待提供真实样本后补验。 |
| ComfyUI 本身 | 未被工作台启动、关闭或重启；验收后无残留 uvicorn/ComfyUI 命令行进程。 |

截图：`screenshots/workflow-page-empty.png`（工作流空列表页面）。
后端访问日志：`logs/r2-uvicorn.log`。

## 数据与安全核对

- 工作流数据目录：`userdata/workflows/`，验收后为空（未产生业务数据）。
- `userdata/` 不提交；原始 workflow 只读；UI workflow 不写入；仅允许写已确认的 `inputs.text` 白名单。
- 未修改 seed、steps、CFG、模型、LoRA、连接、采样器等其他字段（代码白名单约束，由既有测试校验）。
- 未安装或升级 Python、Node、Rust、MSVC；未修改 `main`，未合并分支。

## 异常

- 停止脚本首次因结构化记录缺少进程启动时间而 fail-closed 未杀进程；补齐真实 CreationDate 后二次执行成功停止，端口释放。未误杀其他进程。
- 真机导入链路因缺少真实样本未闭环，已在上表明确标注，不计为已验收。
