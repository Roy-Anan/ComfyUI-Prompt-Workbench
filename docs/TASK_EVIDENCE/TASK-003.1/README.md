# TASK-003.1 工作流导入、解析与 Prompt 白名单写入 — 执行证据（未验收 / 未推送）

> 状态：**代码已按交付落盘，本机实测未通过；后端 6 个 API workflow 测试失败，前端构建通过。
> 按任务书要求，未删除失败用例、未降低测试标准、未跳过校验；未提交、未推送 dev。**

## 1. 基线核对

- 仓库：https://github.com/Roy-Anan/ComfyUI-Prompt-Workbench
- 分支：dev（仅在 dev 工作）
- 起始本地 SHA：`9a76bdbc0bd3ef71a0f389f1782d8a6d13297e59`
- 起始 origin/dev SHA：`9a76bdbc0bd3ef71a0f389f1782d8a6d13297e59`（与本地一致，远端无他人新提交）
- origin/main SHA：`3084866aa85595133c7a1179b15ddd71e659d8f3`（未修改、未合并、未推送）
- 工作区：开始前干净

## 2. 落盘文件清单

新建：

- `backend/workflow_service.py`
- `backend/workflow_api.py`
- `backend/test_workflow_service.py`
- `frontend/src/WorkflowWorkbench.tsx`

修改（仅任务书指定位置）：

- `backend/main.py`：导入 `workflow_router`；`app.include_router(workflow_router)`；`APP_VERSION` → `0.1.0-dev.5`
- `frontend/src/App.tsx`：导入组件、`activePage` 状态、页面导航、设置页/工作流页切换
- `frontend/src/styles.css`：末尾追加工作流页面样式

## 3. 自动化测试结果（现有 venv，Python 3.13.18，pytest 8.4.2）

完整原始输出见 `pytest-output.txt`。

- 后端全部 pytest：**57 collected，51 passed，6 failed**
  - `test_main.py`：32 passed
  - `test_scripts.py`：16 passed
  - `test_workflow_service.py`：**3 passed，6 failed**
- 新增通过的 3 个：
  - `test_ui_workflow_is_parsed_but_not_writable`
  - `test_invalid_workflow_is_rejected`
  - `test_import_rejects_oversized_workflow`
- 失败的 6 个（全部为 API workflow 路径，见 `known-issues.md` 问题 P1）：
  - `test_detect_api_workflow`
  - `test_api_parser_finds_prompt_roles_models_and_lora`
  - `test_prompt_write_changes_only_confirmed_text_fields`
  - `test_write_rejects_unconfirmed_nodes`
  - `test_write_rejects_non_whitelist_mutation`
  - `test_write_rejects_changed_original_fingerprint`

Python 编译检查（`py_compile` 四个后端文件 + main.py）：**通过（exit 0）**。

## 4. 前端构建结果

完整原始输出见 `frontend-build.txt`。

- 命令：`frontend` 目录 `npm run build`（`tsc -b && vite build`）
- 结果：**通过（exit 0）**，33 modules transformed，Vite 5.4.21。
- 说明：初次构建时 JSX 片段闭合被落盘成自闭合 `< />`，与交付源码原文的 `</>` 不符；已按源码原文修正三处 `WorkflowWorkbench.tsx` 与一处 `App.tsx` 后构建通过。

## 5. 真机验收结果

**未执行 / 未完成。** 后端 API workflow 解析链路测试未通过，导入—识别—确认—写入—重启持久化闭环无法在真实界面上走通；按任务书「不要把未执行测试写成通过」的要求，未启动浏览器做界面验收，也未留存界面截图。

- API workflow 实际识别结果：**未取得有效结果**（解析在格式识别阶段即被拒绝）。
- UI workflow 只读识别：仅由单元测试 `test_ui_workflow_is_parsed_but_not_writable` 覆盖通过；未在真实浏览器导入 UI workflow 样本。
- 白名单写入 / 非白名单拒绝：写入相关 4 个用例在导入阶段即失败，未走到写入与拒绝校验。
- 重启后导入记录持久化：未验证。

## 6. 数据保存位置（设计口径，尚未产生真实业务数据）

- 工作流资料根目录：`<userdata>/workflows`（由 `datadir.default_data_root()` 解析到 `userdata/workflows`）。
- 每个工作流一个 UUID 目录：`original.json` / `working.json` / `analysis.json` / `manifest.json` / `versions/`。
- `userdata/` 已被 `.gitignore` 忽略，未进入 Git（本次未产生待提交的 userdata 文件）。

## 7. Git 推送状态

- **未提交、未推送 dev。** 原因：后端新增测试存在失败用例，任务书要求测试通过后再提交推送。
- 本地改动仍在工作区，未覆盖 main、未删除 `legacy-materials/`、未引入 Tauri/Rust/EXE 或新开发环境依赖。

## 8. 尚未解决的实际问题

见 `known-issues.md`。核心为后端交付代码内部的 API workflow 结构口径不一致（待 ChatGPT 侧确认并修正后，再由豆包落地复测）。
