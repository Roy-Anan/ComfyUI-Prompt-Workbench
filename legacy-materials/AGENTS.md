# AGENTS.md — ComfyUI Prompt Workbench 多智能体协作入口

本文件是任何 AI 智能体或人类开发者进入本项目的**规范入口**。它不替代用户手册，只规定：
接手前读什么、哪些事实以哪里为准、什么不能改、改完怎么验证、怎么打包和交接。

项目根目录：

```text
D:\AI\ComfyUI_Prompt_Workbench
```

最终交付包：

```text
dist\ComfyUI_Prompt_Workbench_V2.0.zip
```

---

## 0. 适用范围和优先级

- 适用于所有对本项目做代码、规则、文档、测试、打包、部署改动的智能体。
- 用户是本项目的最终所有者；当用户当前指令与本文件冲突时，以用户当前指令为准，但必须在交付说明中写明影响。
- 本文件与旧文档冲突时，按第 3 节的“事实源优先级”判断，不能凭记忆猜。
- 不允许把本文件或内部实现细节作为对外用户文案输出。

---

## 1. 30 秒了解项目

| 项 | 值 |
| --- | --- |
| 产品 | ComfyUI Prompt Workbench，本机网页工作台 |
| 版本 | V2.0 |
| 页面 | `http://127.0.0.1:8199` |
| 技术栈 | Python 标准库 + 原生 HTML/CSS/JS；无前端框架、无数据库 |
| 推理 | Ollama 桌面版 `http://127.0.0.1:11434`，模型 `comfyui-prompt:v1` |
| 出图 | 秋叶 ComfyUI `http://127.0.0.1:8188` |
| 解释器 | `D:\AI\Qiuye\ComfyUI-aki-v3.2\python\python.exe`（3.13） |
| 入口 | `启动工作台.bat` → `app\server.py` |
| 数据 | `history / settings / workflows / outputs / backups / logs` |
| 发布 | `tools\make_release.py V2.0` → `tools\verify_zip.py V2.0` |

核心能力：按完整 checkpoint 文件名精确匹配 profile，注入规则生成六段提示词，做多轮对话和本地持久化，导入工作流并按连线判定正负节点，提交 ComfyUI 真出图并回显，8GB 显存下自动卸载/恢复 Ollama。

---

## 2. 必读顺序

### 2.1 所有改动前

1. 本文件 `AGENTS.md`；
2. `PROJECT_MANIFEST.json`；
3. `交接说明.md` 的“当前状态 / 工程地图 / 验收清单”；
4. 与你改动模块对应的阶段记录（见第 3 节文档表）。

### 2.2 按任务追加

| 任务 | 追加必读 |
| --- | --- |
| 改后端 / 接口 | `README_使用说明.md` 的“接口”和“注入结构”；对应 `阶段N_实施记录.md` |
| 改前端 | `README` 的“页面怎么用”；`阶段7` 的“前端实装”；`web\` 三个文件 |
| 改规则 / 模型匹配 | `规则包整合记录.md`；`rules\模型数据库.txt`；`profiles\`；`rules_source\模型说明.xlsx` |
| 改显存 / 出图 | `阶段5` / `阶段6` 实施记录；`app\vram_manager.py`；`app\comfy_api.py` |
| 改日志 / 备份 / 设置 | `阶段7_实施记录.md`；`app\workbench_log.py`、`backup.py`、`settings_store.py` |
| 打包 / 发布 | `部署步骤_Windows.md`；`tools\make_release.py`；`tools\verify_zip.py` |

---

## 3. 事实源优先级

发生冲突时按以下顺序判断，**不要用记忆代替读取**：

1. **运行中的代码与配置**：`app\*.py`、`web\*`、`config.json`；
2. **`PROJECT_MANIFEST.json`**：版本、路径、命令、模块、阶段、文档索引；
3. **`README_使用说明.md`**：用户可见行为、接口、数据、匹配规则、边界；
4. **`阶段N_实施记录.md` / `规则包整合记录.md`**：实现过程、测试证据、历史差异；
5. **`更新说明.md`**：版本变化和升级说明。

规则：

- 代码和文档不一致时，**当前行为以代码为准**，但必须在同一次改动中修正文档，不能留下矛盾。
- 旧阶段记录是历史证据，原则上**追加**，不要重写；只有事实错误可以更正，并注明“更正日期 / 原因”。
- 文档不能凭空写“已测试”“已完成”；没有真实运行证据的，写“未测 / 待核实”。

---

## 4. 目录和所有权

| 路径 | 归属 | 写入规则 |
| --- | --- | --- |
| `app\` | 后端 | 一模块一职责；新增模块必须登记到 manifest 的 `app_modules` |
| `web\` | 前端 | 只改这三个文件；新增静态资源要同步 server 静态路由和 UI 自检 |
| `tests\` | 测试 | 新阶段建 `test_stageN.py`；不得删除旧测试来“让测试通过” |
| `tools\` | 开发 / 发布工具 | 不放运行时依赖；新增工具登记到 manifest |
| `rules\` | 运行时规则 | 改规则必须留来源和测试；`模型数据库.txt` 是精确匹配唯一登记表 |
| `profiles\` | 模型 profile | 每个模型一个文件；参数依据标记原样保留 |
| `rules_source\` | 规则原始资料 | 原则只读；改前记录来源、SHA256、日期 |
| `history\` | 用户数据 | 只能通过应用接口读写；不手工改，不打包 |
| `settings\` | 用户数据 | 只能通过设置接口改；不打包 |
| `outputs\` | 用户出图 | 保留；不自动删；不打包 |
| `workflows\` | 用户工作流 | 通过工作流库接口管理；不打包 |
| `backups\` | 用户备份 | 删除只进 `_trash`；不打包 |
| `logs\` | 运行 / 测试证据 | 不记录提示词和对话正文；打包只带测试证据 |
| `dist\` | 发布产物 | 不放源码副本；不递归打包 |

---

## 5. 不可破坏的约束（MUST）

1. **精确匹配，不做模糊匹配**：只认 `rules\模型数据库.txt` 登记的完整 checkpoint 文件名；允许去目录前缀和大小写差异，但不做关键词、前缀、相似度匹配。
2. **不写死节点编号**：正负节点按工作流连线判定，禁止固化“正向=节点 4、负向=节点 5”。
3. **不改写参数依据标记**：`[已核实]`、`[镜像核实]`、`[作者推荐]`、`[作者示例]`、`[作者指南]`、`[已实测]`、`[起始测试值]`、`[待核实]`、`[未给出]` 原样保留。
4. **8GB 显存默认 `batch_size=1`**；不要让 Ollama 与 ComfyUI 同时驻留还宣称没问题。
5. **Ollama 必须连桌面版服务**：不要自己起 `ollama serve`；模型库在 `D:\AI\MODELS`，由桌面版 App 管理。
6. **只监听本机**：`127.0.0.1`；不擅自改成 `0.0.0.0` 或加公网访问。
7. **主题只实现深色**：`theme` 非 `dark` 会被强制回 `dark`；不要假装支持浅色。
8. **用户数据不打包**：`history / settings / outputs / backups` 绝不进 ZIP；`dist` 不递归。
9. **删除不抹除**：会话删除进 `_archive`，备份删除进 `_trash`；不要直接 `rm` 用户数据。
10. **不编造完成**：没有真实测试/出图证据，不写“已通过”；400 校验失败也计入错误并写日志。
11. **日志不记正文**：`workbench_log` 只记操作、结果、路径摘要，不记提示词和对话正文。
12. **改动可回滚**：设置保存前留 `app_settings.bak.json`；升级不覆盖用户数据；发布包可回溯。

---

## 6. 变更协议（每次改动照此执行）

### 第 1 步：定义范围

在开始前写清：

- 要改哪些文件；
- 不改哪些文件；
- 属于哪个阶段 / 哪个模块；
- 验收标准是什么（测试、UI、真机、打包）。

### 第 2 步：先读再动

- 读本文件、manifest、相关阶段记录；
- 搜索是否已有同类文档、测试、接口，避免重复造；
- 读目标文件的当前内容，不要按记忆改。

### 第 3 步：最小改动

- 不顺手重构无关模块；
- 不批量改写旧文档措辞；
- 不引入新依赖；确需引入时先说明理由、安装位置和回退方式；
- 不删除旧测试、旧记录、旧备份。

### 第 4 步：实现 + 测试

- 后端改动：补/改单元测试；跑 `python -m unittest discover -s tests -v`；
- 真机链路：跑 `tests\smoke_server.py`（先备份用户数据、确认 8199 空闲）；
- 前端改动：跑 `tools\check_ui.py`；有条件跑 `tools\ui_probe.py`；
- 交接结构改动：跑 `tools\check_handover.py`。

### 第 5 步：同步文档

按改动类型更新**唯一指定位置**：

| 改动 | 必须更新 |
| --- | --- |
| 用户可见功能 / 操作 | `README_使用说明.md` |
| 版本行为变化 / 升级 | `更新说明.md` |
| 阶段级实现 | `阶段N_实施记录.md` |
| 规则 / 模型来源 | `规则包整合记录.md` 或对应阶段记录 |
| 路径 / 命令 / 模块 / 阶段 / 文档索引 | `PROJECT_MANIFEST.json` |
| 交接入口 / 验收 | `交接说明.md` |
| 协作规则 | 本文件 `AGENTS.md` |

不允许新建 `README2.md`、`说明_新.md`、`最终版.md` 之类的平行文档。新增长文档必须先登记到 manifest 的 `docs_index`。

### 第 6 步：打包和验证

```bat
cd /d D:\AI\ComfyUI_Prompt_Workbench
set PY=D:\AI\Qiuye\ComfyUI-aki-v3.2\python\python.exe
"%PY%" tools\check_handover.py
"%PY%" tools\make_release.py V2.0
"%PY%" tools\verify_zip.py V2.0
```

发布包必须满足：

- 关键文件齐全；
- ZIP CRC 通过；
- 无嵌套 ZIP / `dist`；
- 无 `__pycache__`；
- 无 `history / settings / outputs / backups`；
- 包内包含交接文档和 manifest。

### 第 7 步：交付说明

最终回复必须写清：

- 改了什么；
- 用什么真实测试验证；
- 哪些没测 / 有边界；
- 产物路径；
- 如果改动了版本或包，写清新的版本和包状态。

---

## 7. 扩展模板

### 7.1 新增一个阶段

1. 建 `阶段N_实施记录.md`，记录“计划要求 → 实现 → 测试 → 差异 → 欠账”；
2. 建 `tests\test_stageN.py`；
3. 在 `PROJECT_MANIFEST.json` 的 `stages` 增加一条，`status` 用 `done` 或 `in_progress`；
4. 用户可见部分更新 `README`；
5. 版本变化更新 `更新说明`；
6. 打包验证。

### 7.2 新增后端模块

1. 文件放 `app\`，模块 docstring 写职责；
2. 在 `PROJECT_MANIFEST.json` 的 `app_modules` 登记；
3. 若新增 API，更新 `app\server.py` 顶部路由文档、`README` 接口表、manifest 的 `api_contract_doc` 指向；
4. 补单元测试；
5. 不要让新模块偷偷读写用户数据目录，必须走现有 store。

### 7.3 新增设置项

1. 在 `app\settings_store.py` 加默认值、类型、白名单/范围校验；
2. 前端设置页加控件，并处理保存失败；
3. `README` 设置表更新；
4. `tests\test_stage7.py` 或新测试覆盖非法值；
5. 不把新设置写进 `config.json` 以外的地方，避免双份事实。

### 7.4 新增模型

按 `README` 的“加新底模”：

1. 复制模板到 `profiles\`；
2. `rules\模型数据库.txt` 加完整文件名映射；
3. `rules\模型索引_Ollama.txt` 补索引；
4. 跑 profile 匹配和完整性测试；
5. 不修改 `rules_source\ComfyUI_Prompt_Master_V1` 原始文件；确需更新时另记来源。

### 7.5 新增 API

1. 在 `app\server.py` 的 `do_GET` / `do_POST` 路由实现；
2. 顶部 docstring 补一行；
3. `README` 接口表补一行；
4. 前端调用处同步；
5. 单元测试覆盖成功 + 失败；
6. 不改旧接口语义；要改就升版本并在 `更新说明` 写行为变化。

---

## 8. 禁止事项

- 禁止把用户数据、备份、出图原图打进发布 ZIP。
- 禁止直接删除 `history\`、`settings\`、`outputs\`、`backups\` 里的用户文件。
- 禁止在没有备份的情况下跑会写数据的冒烟测试。
- 禁止用模糊匹配“猜”模型 profile。
- 禁止把 `正向=4 / 负向=5` 这类工作流节点编号写死。
- 禁止修改规则文件里的参数依据标记来“统一格式”。
- 禁止把 `theme` 说成支持浅色。
- 禁止声称“已验证”但没有测试记录 / 出图证据。
- 禁止在 `logs\` 里记录提示词或对话正文。
- 禁止引入前端框架、数据库、账号体系来“重构”这个本机小工具；除非用户明确要求。
- 禁止把 `rules_source` 的原始规则包和运行时 `rules` 混为一谈。

---

## 9. 完成定义（Definition of Done）

一个改动只有同时满足以下条件才算完成：

- [ ] 代码可运行，未破坏既有功能；
- [ ] 单元测试通过，且新增行为有测试；
- [ ] 涉及真机链路的，有真实冒烟 / 出图证据；
- [ ] 相关文档已更新到唯一指定位置；
- [ ] `PROJECT_MANIFEST.json` 已同步（路径 / 命令 / 模块 / 阶段 / 文档）；
- [ ] `tools\check_handover.py` 通过；
- [ ] 发布包已重新生成并通过 `verify_zip.py`；
- [ ] 最终说明写清改了什么、测了什么、没测什么、产物在哪。

---

## 10. 常用命令

```bat
cd /d D:\AI\ComfyUI_Prompt_Workbench
set PY=D:\AI\Qiuye\ComfyUI-aki-v3.2\python\python.exe

REM 启动
"%PY%" app\server.py

REM 启动并自动打开默认浏览器（双击 启动工作台.bat 走这条）
"%PY%" app\server.py --open-browser

REM 强制不弹浏览器（脚本/测试用）
"%PY%" app\server.py --no-browser

REM 单元测试
"%PY%" -m unittest discover -s tests -v

REM 真机冒烟（先停 8199、先备份用户数据）
"%PY%" -u tests\smoke_server.py

REM 静态 UI 自检
"%PY%" tools\check_ui.py

REM 浏览器 UI 自检（需要 Chrome + websocket-client）
"%PY%" tools\ui_probe.py

REM 交接结构自检
"%PY%" tools\check_handover.py

REM 打包 + 校验
"%PY%" tools\make_release.py V2.0
"%PY%" tools\verify_zip.py V2.0
```

---

## 11. 当前基线（2026-11-15）

- 版本：V2.0；`app\__init__.py` 与 `config.json` 的 `app.version` 都是 `2.0`。
- 阶段 1–7 完成；阶段 1 的实现记录在 `规则包整合记录.md`。
- 测试基线：单元 129/129；冒烟 128/128；浏览器 UI 22/22。
- 最终包：`dist\ComfyUI_Prompt_Workbench_V2.0.zip`。
- 交付包默认不自动起服务；若用户已手动启动工作台，8199 可能正在监听。ComfyUI 8188 和 Ollama 11434 独立运行。
- 详细证据：`logs\测试结果_阶段7.txt`、`logs\冒烟结果_阶段7.txt`、`logs\阶段7_UI自检结果.json`、`logs\UI截图_阶段7_*.png`。

基线不是永久承诺：后续改动必须更新 `PROJECT_MANIFEST.json` 和对应记录，不能只改代码不改文档。

---

## 12. 遇到不确定时

1. 先查 `PROJECT_MANIFEST.json` 和 `README`，不要猜；
2. 再查对应阶段记录和代码；
3. 仍不确定，向用户说明“缺什么信息、会影响什么”，不要擅自改共享数据或删除文件；
4. 发现文档与代码冲突，记录冲突点，修代码或修文档，二选一必须落地，不能两边都留着。
