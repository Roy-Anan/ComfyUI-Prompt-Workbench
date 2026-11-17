# Doubao-Receipt — TASK-003.1 豆包原始回执

> 本文件按证据归档规则保留豆包本次任务完成后给出的完整原始回执原文，未做结论摘录或润色。
> 佐证材料见同目录：`README.md`、`known-issues.md`、`pytest-output.txt`、`frontend-build.txt`。
> 任务状态：**代码已落盘，后端 6 个新增测试未通过；未提交、未推送 dev；真机闭环验收未执行。**
> 记录日期：2026-11-17。

---

## TASK-003.1 执行回执（未验收 / 未推送）

**结论先行：代码已按你交付的内容落盘；后端新增测试 6 失败、现有 51 项全过；前端构建通过。按任务书「测试失败不推送、不虚报通过」的要求，本次未提交、未推送 dev，真机闭环验收未执行。**

### 1. Git 基线
- 仓库：https://github.com/Roy-Anan/ComfyUI-Prompt-Workbench
- 起始 SHA（本地 = origin/dev）：`9a76bdbc0bd3ef71a0f389f1782d8a6d13297e59`
- 最终 SHA：**未提交，仍为 `9a76bdb…`**
- main：本地 / origin/main 均为 `3084866aa85595133c7a1179b15ddd71e659d8f3`，**未改、未合并、未推送**
- 工作区：改动保留在本地，未入库；`userdata/`、`frontend/dist/` 均未被 Git 跟踪

### 2. 文件清单
新建：
- `backend/workflow_service.py`
- `backend/workflow_api.py`
- `backend/test_workflow_service.py`
- `frontend/src/WorkflowWorkbench.tsx`

修改（仅指定位置）：
- `backend/main.py`：导入 `workflow_router`、`app.include_router(workflow_router)`、`APP_VERSION` → `0.1.0-dev.5`
- `frontend/src/App.tsx`：组件导入、`activePage` 状态、导航、页面切换
- `frontend/src/styles.css`：末尾追加工作流页面样式

### 3. Python 测试（.venv Python 3.13.18，pytest 8.4.2）
- 全部：**57 collected，51 passed，6 failed**
  - `test_main.py` 32 passed；`test_scripts.py` 16 passed（既有基线无回归）
  - `test_workflow_service.py`：**3 passed / 6 failed**
- 通过：UI workflow 只读解析、非法格式拒绝、20MB 超限拒绝
- 失败（全部卡在 API workflow 格式识别阶段）：
  - `test_detect_api_workflow`
  - `test_api_parser_finds_prompt_roles_models_and_lora`
  - `test_prompt_write_changes_only_confirmed_text_fields`
  - `test_write_rejects_unconfirmed_nodes`
  - `test_write_rejects_non_whitelist_mutation`
  - `test_write_rejects_changed_original_fingerprint`
- `py_compile` 四个后端文件 + main.py：**通过（exit 0）**

### 4. 前端构建
- `npm run build`（`tsc -b && vite build`）：**通过（exit 0）**，33 modules，Vite 5.4.21
- 过程中发现一处落盘偏差：JSX 片段闭合被写成自闭合 `< />`，与你源码原文的 `</>` 不符；已按原文修正（`WorkflowWorkbench.tsx` 三处、`App.tsx` 一处）后构建通过。

### 5. 真机验收：未执行
后端 API 解析链路未通过，导入—识别—确认—写入—重启持久化闭环无法在真实界面走通；按口径未启动浏览器验收、未留界面截图，也未把合成测试说成真实工作流验收。
- API workflow 识别结果：未取得有效结果（格式识别阶段即被拒）
- UI workflow 只读：仅单元测试覆盖通过，未在浏览器导入样本
- 白名单写入 / 非白名单拒绝 / 重启持久化：均未走到，不能视为已验证

### 6. 阻塞问题（待你侧确认口径，我未自行改核心实现）
**P1：后端解析器与测试样本的 API 结构口径不一致。**
- 测试样本是 ComfyUI 标准扁平结构：根对象直接挂 `"1"…"6"` 节点。
- 交付的 `workflow_service.py` 里 `detect_format`（第 63–80 行）和 `_api_nodes`（第 81–85 行）都从 `workflow["nodes"]` 取节点；扁平样本无此键，直接抛 `WorkflowError: 无法识别工作流格式…`。
- 错误原文与逐用例定位见 `known-issues.md`。
- 需你二选一：① 解析器适配扁平 API prompt；② 测试样本改为 `nodes` 包裹结构。确定后我再落地复测。

### 7. 数据位置（设计口径，尚未产生真实业务数据）
- 工作流根目录：`userdata/workflows/<uuid>/`（`original.json` / `working.json` / `analysis.json` / `manifest.json` / `versions/`）
- 本次未产生待提交的 userdata 文件。

### 8. 未上传 / 未做项
- 未提交、未推送 dev；未改 main；未删 `legacy-materials/`；未引入 Tauri/Rust/EXE 或新环境依赖
- 未做 Ollama 接入、自动生成 Prompt、模型知识库、GPU 调度、ComfyUI 队列、自动出图、UI 美化、EXE 封装
- 敏感扫描：main.py 命中的 token/secret 均为既有会话认证逻辑（`secrets` 标准库、启动票据/CSRF 校验），无硬编码密钥；无数据库、模型权重、原始图片入库

证据已归档至 `docs/TASK_EVIDENCE/TASK-003.1/`（README、known-issues、pytest 原始输出、前端构建结果）。等你确认 P1 口径或给出修正后的代码，我再继续复测与提交。
