# PROJECT_STATE — 项目当前状态

- 任务编号：TASK-002.3
- 记录日期：2026-11-17
- 记录人：豆包
- 状态口径：如实记录，计划中的功能一律不计为已完成；仅代码未验证的项明确标注“未验证”

## 1. 当前所处阶段

- 阶段：**M0 基础骨架阶段**（本机 Web 架构切换与一键启动基础，不开发新产品功能）。
- 当前任务：**TASK-002.3** —— 切换本机 Web 架构并完成一键启动基础。
- 开发分支：`dev`（起始基线 `e53969b23e8081e86ed65ba6ee9b2725d17c0966`，尚未合并 main）。
- 版本：`0.1.0-dev.3`。
- **方向变更（2026-11-17，TASK-002.3）**：产品正式从 Tauri 桌面方向切换为本机浏览器 Web 应用；不再以 EXE 安装包为交付目标，不再继续开发 Tauri/Rust 桌面宿主；默认通过本机浏览器访问 `http://127.0.0.1:8000`，默认只绑定 `127.0.0.1`。历史 Tauri/Rust 代码归档于 `legacy/src-tauri/`，不属于 Web 运行时。

## 2. 本次已实际完成并验证的事项

- 按任务书完整替换后端与测试：`backend/main.py`、`backend/test_main.py`；完整替换前端 `frontend/src/App.tsx`；局部修改 `frontend/src-tauri/src/lib.rs`；在保留原布局基础上合并 `frontend/src/styles.css` 新样式。
- Python 后端（本机独立 `.venv`，Python 3.13.18）：
  - 语法编译检查通过（`py_compile`，main.py / test_main.py 退出码均 0）。
  - pytest 13 项全部通过（6.19s，1 条 StarletteDeprecationWarning，非失败）。
  - 真实 HTTP 冒烟（临时数据根、端口 14512、令牌 `smoke-token-abc`）：
    - 无令牌 / 错令牌均返回 401；正确令牌 `/api/health` 200，返回 `ok:true`、版本 `0.1.0-dev.2`。
    - CORS 预检：`http://127.0.0.1:1420` 与 `http://localhost:1420` 均 200 且返回对应 `access-control-allow-origin`；未授权 Origin `https://untrusted.example` 返回 400 且无 allow-origin 头。
    - SQLite 真实创建于临时数据根 `database/workbench.sqlite3`（16384 字节），含 `schema_version`、`app_metadata` 两表，`schema_version=1`；重复初始化两次后版本仍为 1。
    - 损坏 `settings.json` 被备份为 `settings.corrupt-20261117-214728-86f950.json`，恢复后 root 取宿主固定数据根。
    - 修改 `storage.root` 返回 400（detail 含 fixed）；未知存储键返回 400；`checkpoint`/`lora` 允许留空；离线 Ollama / ComfyUI 返回 `online:false`，服务 200 不崩溃。
- 前端：
  - TypeScript 类型检查 `tsc -b` 退出码 0，无类型错误。
  - Vite 生产构建成功（`tsc -b && vite build`，33 模块，659ms，产物 `dist/`）。
- 安全口径与代码一致：后端仅绑定 `127.0.0.1`；随机会话令牌；API 必须携带 Bearer 令牌；root 由宿主固定、前端不把只读 root 发回后端；退出时只结束 Tauri 自己创建的子进程（该退出清理路径属 Rust 代码，未在本机实测，见第 3 节）。

## 3. 尚未完成 / 未验证事项

### 3.1 受本机环境阻塞，未能实测（仅有代码，未验证）

- **Rust / Tauri 编译检查（`cargo check`）未执行成功**：本机未安装 Rust 工具链（`cargo`、`rustc`、`rustup` 均不在 PATH）。
- **MSVC C++ Build Tools 未安装**：`cl.exe` 不在 PATH，`vswhere.exe` 不存在；即使装上 Rust，Windows 上链接 Tauri 也需要该工具链。
- **桌面窗口启动、Tauri 自动拉起 Python 子进程、前端经 Tauri 命令取得随机端口与令牌、退出时子进程清理**：上述闭环依赖 Rust 编译与 Tauri 运行时，因工具链缺失未能在本机跑通，仅完成代码落地与静态通读核对。
- **WebView2 运行时**：注册表 `{F3017226-...}` 读到版本 `157.0.4341.46`；本机 Edge 版本 `157.0.4341.60` 存在；WebView2 在 Tauri 壳内的实际可用性仍需安装工具链后实测。

### 3.2 环境版本与任务书要求的偏差

- 任务书要求 **Python 3.12**；本机 PATH 默认 Python 为 **3.13.18**（venv），另有 3.9（64/32），**未安装 Python 3.12**。本次后端在 3.13.18 下通过测试；3.12 兼容性尚未验证。

### 3.3 业务边界（本次明确不实现，详见任务书）

- 完整 Prompt 编辑器、模型知识库、角色管理 UI、注入文件编辑 UI、ComfyUI 工作流解析、Prompt 写入工作流、LLM 显存调度、自动启停 ComfyUI、Windows 正式安装包、数据库迁移工具、原生文件夹选择器。
- Ollama / ComfyUI 本次仅检测连接，不自动启动、不关闭、不重启。

### 3.4 其他遗留

- 旧项目素材已归档到 `legacy-materials/`，尚未逐文件审查；规则文本、模型档案、提示词模板的可信度需在 M3 规则引擎阶段重新核对。
- 当前没有经过真实 Windows 桌面端到端验收的完整新产品；现有通过记录仅限后端 HTTP/单元测试与前端静态构建。

## 4. 后续任务（待安排）

1. 在本机安装 Rust 工具链与 MSVC C++ Build Tools（或在具备工具链的环境中），完成 `cargo check`、`tauri dev` 桌面窗口启动、sidecar 自动拉起、端口/令牌握手、退出清理的真机验收。
2. 按需要固定 Python 3.12 虚拟环境并复核兼容性。
3. M1/M2：工作流解析与白名单完整性保护；其余阶段按 `docs/ROADMAP.md` 顺序推进。

## 4.1 TASK-002.2 环境盘点追加记录（2026-11-17）

- 任务性质：只读环境盘点与交付准备，未安装任何开发软件，未修改系统设置。
- 证据目录：`docs/TASK_EVIDENCE/TASK-002.2/`。
- 实测要点：Windows 11 家庭版 26200 x64；当前用户非管理员；WebView2 Runtime 157.0.4341.46 已装；Edge 157.0.4341.60；本机 Python 3.13.18（系统/py 另列 3.9），项目 `.venv` 3.13.18，无 Python 3.12；Rust/MSVC 缺失；C 盘剩余 45.95 GB、D 盘剩余 49.11 GB。
- 结论：用户当前不需要安装任何开发软件；桌面闭环与正式 EXE 仍未完成，等待打包方案与打包环境。

## 5. 阻塞问题与风险

- **阻塞（阻断桌面闭环验证）**：Rust 工具链缺失、MSVC C++ Build Tools 缺失。这是本机环境问题，非本次代码改动引入。
- **待观察风险**：Tauri sidecar 启动与打包、loopback 安全握手在真机上的表现、WebView2 兼容性、杀毒误报（见 `docs/decisions/ADR-0001-TECH-STACK.md`）。
- 真机显存阈值与释放行为尚未测量，M6 前不得硬编码为保证值。

## 6. 验收情况记录

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| Python 语法检查 | 通过 | `py_compile main.py / test_main.py` 退出码 0 |
| Python pytest | 通过 | 13 passed，6.19s（pytest 8.4.2 / Python 3.13.18，1 条弃用警告） |
| 无 / 错令牌被拒绝 | 后端已实测通过 | 均返回 401 |
| 正确令牌健康检查 | 后端已实测通过 | 真实 uvicorn 返回 200，`ok:true`，版本 0.1.0-dev.2 |
| CORS 白名单预检 | 后端已实测通过 | 127.0.0.1:1420 / localhost:1420 200 且带 allow-origin；未授权 Origin 400 无 allow-origin |
| SQLite 创建与表结构 | 后端已实测通过 | `workbench.sqlite3` 16384 字节，两表存在，schema_version=1 |
| 重复初始化保留版本 | 后端已实测通过 | 再初始化两次后 schema_version 仍为 1 |
| root 修改被拒绝 | 后端已实测通过 | 400，detail 含 fixed |
| 未知存储键被拒绝 | 后端已实测通过 | 400 |
| 外部模型路径可留空 | 后端已实测通过 | checkpoint / lora 空值保存 200 |
| 损坏配置备份与恢复 | 后端已实测通过 | 备份 `settings.corrupt-20261117-214728-86f950.json`，恢复 200 |
| 路径校验可创建目录 | 后端已实测通过 | `/api/storage/validate` 200，存在/目录/可写均 true |
| Ollama / ComfyUI 离线不崩溃 | 后端已实测通过 | 两者离线返回 `online:false`，服务 200 |
| 前端 TypeScript 检查 | 通过 | `tsc -b` 退出码 0，无类型错误 |
| 前端 Vite 构建 | 通过 | `vite build` 成功，33 模块，659ms，产物 `dist/` |
| Rust 编译检查 | 阻塞未执行 | 本机无 cargo/rustc/rustup，无 MSVC 链接器 |
| 桌面窗口启动 | 未验证 | 依赖 Rust/Tauri，工具链缺失 |
| Tauri 自动启动 Python 服务 | 未验证 | 依赖 Rust 编译 |
| 取得随机端口与会话令牌 | 未验证 | 依赖 Tauri 命令 `get_backend_config`，未在壳内运行 |
| 退出只结束自己的 Python 子进程 | 未验证 | 属 Rust 退出事件代码，未编译运行 |
| 真实出图端到端验收 | 未完成 | 不在本次边界内 |

## 7. 状态更新规则

- 只有在对应任务完成并有可核对证据（测试记录、真机验收或远程提交）后，才把事项标记为已完成。
- 每次交付后更新本文件的阶段、已完成、未完成、阻塞与验收记录，并在 `PROJECT_CHANGELOG.md` 留痕。
- 无法确认的状态记为 unknown / 未验证，不推断成功或失败。

## 8. TASK-002.3 本机 Web 架构切换记录（2026-11-17）

### 8.1 本次已实际完成并验证

- **架构切换**：FastAPI 同时托管前端 `frontend/dist/` 静态产物与本机 API；前端改为同源相对路径 fetch，不再经 Tauri `invoke` 取端口/令牌。
- **Web 安全方案**：`/api/bootstrap` 为同源回环浏览器签发进程内会话票据（HttpOnly Cookie `workbench_session`）与可读 CSRF Cookie `workbench_csrf`；状态变更请求需携带 `X-Workbench-CSRF` 头；Origin 白名单校验；非安全方法拒绝未授权来源；引导令牌仅经环境变量用于脚本/CLI/测试，不写入前端构建文件。
- **静态托管与 SPA 回退**：`/api/` 前缀未命中返回 JSON 404（不返回 HTML）；`dist/` 缺失返回 503 明确错误；深层非 API 路由回退 `index.html`；路径越出 dist 返回 403。
- **一键启停**：`启动工作台.bat` / `停止工作台.bat` 入口；`scripts/workbench_launcher.py` 复用项目 `.venv`，检查 8000 占用与重复实例，健康检查通过后开浏览器；`scripts/workbench_stopper.py` 按记录 PID 终止工作台进程树，不按名称杀 Python，不影响 Ollama / ComfyUI / 其他 Python 服务。
- **测试与真机验收**：pytest 20 项通过；`tsc -b` 与 `vite build` 通过；真实 Edge 浏览器访问 `http://127.0.0.1:8000`，服务卡片显示已连接（Python 3.13.18），设置/存储/连接数据正常渲染，刷新后 SPA 回退与会话保持正常；重复启动识别已有实例不冲突；停止后端口释放、PID 清除，再次启动成功；监听仅 `127.0.0.1:8000`。
- **保留项**：SQLite 初始化与版本管理、数据根 `%LOCALAPPDATA%\ComfyUI-Prompt-Workbench`、设置管理 API、目录初始化、Checkpoint/LoRA 外部目录、Ollama/ComfyUI 连接配置与只读检测、API 认证、损坏配置备份机制均保留，数据结构未无故改变。

### 8.2 尚未完成 / 未验证事项

- 业务功能（Prompt 编辑器、知识库、角色管理、工作流解析、规则引擎、队列、显存调度、出图闭环等）仍属后续阶段，本次未实现。
- Python 3.12 兼容性仍未验证（本机 `.venv` 为 3.13.18，测试在 3.13.18 下通过）。
- 未安装 Rust/MSVC/Node 开发工具；正式运行不要求 Node 开发服务器，Node 仅用于构建前端产物。
- Ollama / ComfyUI 本次仅做连通性检测，未在两者在线状态下做真实调用验收。

### 8.3 验收情况记录（TASK-002.3）

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| Python 编译检查 | 通过 | `py_compile` 退出码 0 |
| Python pytest | 通过 | 20 passed，Python 3.13.18 / pytest 8.4.2，1 条 StarletteDeprecationWarning |
| TypeScript 类型检查 | 通过 | `tsc -b` 退出码 0 |
| Vite 生产构建 | 通过 | `vite build`，32 模块，产物 `dist/` |
| SQLite 创建与版本保留 | 通过 | `workbench.sqlite3` 两表，schema_version=1，重复初始化保留 |
| API 认证（成功/失败） | 通过 | 无会话 401；票据/Bearer 授权 200；外部 Origin 状态变更 403 |
| CSRF 防护 | 通过 | Cookie 会话缺 CSRF 头 403；带头 200 |
| 浏览器真实访问 | 通过 | Edge 访问 127.0.0.1:8000，已连接并渲染设置页 |
| SPA 刷新回退 | 通过 | 刷新后重新 bootstrap，数据正常回填 |
| 端口绑定 | 通过 | 仅监听 127.0.0.1:8000，未绑 0.0.0.0 |
| 重复启动 | 通过 | 识别已有实例，不产生第二个进程 |
| 停止生命周期 | 通过 | 按 PID 终止进程树，端口释放，PID 文件清除 |
| 停止后再启动 | 通过 | 再次启动成功，根路径 200 |
| Ollama 离线兼容 | 通过 | 离线返回 online:false，服务 200 不崩溃 |
| ComfyUI 离线兼容 | 通过 | 离线返回 online:false，服务 200 不崩溃 |
| 用户数据保护 | 通过 | 数据根在 LOCALAPPDATA，未进构建目录；未删除/重建数据库 |
| 真实出图端到端验收 | 未完成 | 不在本次边界内 |

## 9. TASK-002.3.1 本机 Web 安全加固与项目内数据目录迁移记录（2026-11-17）

### 9.1 本次已实际完成并验证

- **数据目录迁移**：默认数据根从 `%LOCALAPPDATA%\ComfyUI-Prompt-Workbench` 迁到项目内 `userdata/`（`WORKBENCH_DATA_ROOT` 可覆盖）；新增 `backend/datadir.py` 统一路径、子目录、迁移备份与完整性校验。旧库完整性 ok，迁入前在 `userdata/backups/legacy-migration-20261117-145437/` 备份；旧目录原样保留；`userdata/` 被 `.gitignore` 忽略，不入库。
- **安全加固**：启动器前置 loopback 校验；停止器按可执行路径 + 命令行 + 启动时间核验身份、fail-closed、递归回收进程树；静态路径改为解码后真实路径包含判断，拒绝穿越与相邻前缀碰撞；`/api/health` 作为未认证身份探测并携带应用标识，启动器据此核验实例身份。
- **测试与构建**：pytest 36 passed（Python 3.13.18 / pytest 8.4.2，1 条 StarletteDeprecationWarning）；`tsc -b` 与 `vite build` 通过（32 模块）。
- **真机验收**：Edge 访问 `127.0.0.1:8000`，服务已连接（Python 3.13.18），存储根目录显示为项目内 `userdata`；仅监听 `127.0.0.1:8000`；受保护端点无会话仍 401。
- **证据归档**：`docs/TASK_EVIDENCE/TASK-002.3.1/`（报告、test-results、logs、screenshots、git-diff）。

### 9.2 尚未完成 / 未验证事项

- Python 3.12 兼容性未验证（本机 `.venv` 为 3.13.18）。
- Ollama / ComfyUI 在线状态下的真实调用与出图闭环未验收；本次仅离线连通性检测。
- 业务功能（编辑器、知识库、规则引擎、工作流解析、队列、草稿版本、显存调度、生成历史等）属后续阶段，本次未实现。
- 会话票据存进程内存，重启后需重新 bootstrap，属当前设计。

### 9.3 验收情况记录（TASK-002.3.1）

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| Python pytest | 通过 | 36 passed，Python 3.13.18 / pytest 8.4.2，1 条弃用警告 |
| TypeScript 检查 | 通过 | `tsc -b` 退出码 0 |
| Vite 生产构建 | 通过 | 32 模块，产物 `dist/` |
| 新根目录初始化 | 通过 | 10 个管理子目录 + `settings/` 建立 |
| 旧库 / 新库完整性 | 通过 | 两侧 `integrity_check` = ok，schema_version=1 |
| 迁移备份与旧数据保留 | 通过 | 备份目录保留旧库；旧根两文件原样存在 |
| `userdata` 忽略 | 通过 | `git check-ignore` 命中 `/userdata/` |
| 监听地址限制 | 通过 | 仅监听 127.0.0.1:8000；非回环地址被拒 |
| PID 身份核验 | 通过 | 身份不匹配 fail-closed；匹配时回收进程树 |
| 静态路径安全 | 通过 | 穿越 / 编码穿越 / 前缀碰撞均拒绝；正常资源可访问 |
| 健康身份探测 | 通过 | 无会话 200 带应用标识；受保护端点仍 401 |
| 浏览器真机验收 | 通过 | Edge 已连接，存储根为项目内 userdata |
| 真实出图端到端验收 | 未完成 | 不在本次边界内 |

## 10. TASK-002.3.2 进程身份校验加固与旧设置迁移记录（2026-11-17）

### 10.1 本次已实际完成并验证

- **进程身份结构化记录**：启动器写入 `.workbench-runtime.json`（PID、ISO8601 启动时间、可执行路径、工作目录、命令行、随机实例标识、host/port）；停止器读取记录并逐项比对 app_id、实例标识（经本机健康检查回传）、PID、可执行路径、工作目录、命令行、CreationDate；记录缺失/损坏或任一不匹配 fail-closed，不杀进程；正常停止后清理记录与旧 PID 文件；仅回收本工作台进程树，不按名称批量杀 Python。
- **旧设置无损迁移**：`backend/datadir.py` 新增设置单独迁移通道；保留 Ollama/ComfyUI 地址、Checkpoint、LoRA 路径及其他已有偏好；管理路径按新 userdata 重建；新设置已存在时安全合并、冲突保留已有用户值并记录；迁移前备份旧设置；未知字段保留在 `_legacy_extra`；不重迁数据库，旧 AppData 目录保留。
- **测试与真机**：pytest 48 passed（Python 3.13.18 / pytest 8.4.2，1 条 StarletteDeprecationWarning）；真机启动就绪（PID 7908），健康检查实例标识与记录一致，身份核验通过，正常停止后进程树回收、8000 端口释放、记录清理。
- **证据归档**：`docs/TASK_EVIDENCE/TASK-002.3.2/`（README、test-results、logs、git-diff、known-issues）。

### 10.2 尚未完成 / 未验证事项

- Python 3.12 兼容性未验证（本机 `.venv` 为 3.13.18）。
- Ollama / ComfyUI 在线状态下的真实调用与出图闭环未验收；本次仅离线连通性与身份探测。
- 业务功能（Prompt 注入、知识库、规则引擎、工作流解析、队列、草稿版本、显存调度、生成历史等）属后续阶段，本次未实现。
- 会话票据存进程内存，重启后需重新 bootstrap，属当前设计。

### 10.3 验收情况记录（TASK-002.3.2）

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| Python pytest | 通过 | 48 passed，Python 3.13.18 / pytest 8.4.2，1 条弃用警告 |
| 结构化运行记录 | 通过 | 含 PID/启动时间/路径/工作目录/命令行/实例标识 |
| 启动时间真正比对 | 通过 | 记录 CreationDate 与活动进程 CreationDate 逐项比较 |
| 身份不匹配拒绝终止 | 通过 | 时间/路径/命令行/实例标识不一致均 fail-closed |
| 记录损坏 fail-closed | 通过 | 缺失/损坏记录不杀进程并给出明确错误 |
| 正常停止清理记录 | 通过 | 停止后 runtime.json 与 PID 文件均不存在 |
| 旧设置字段保留 | 通过 | 连接地址、checkpoint、lora 保留；管理路径指向新根 |
| 安全合并不覆盖 | 通过 | 新设置已存在时保留已有用户值，冲突记入报告 |
| 旧设置备份 | 通过 | 隔离复现生成 `legacy-settings-<timestamp>.json`；本机新设置已存在走合并 |
| 数据库未重迁 | 通过 | 旧库保留，新库沿用既有数据，未重建/覆盖 |
| 真机启动/访问/停止 | 通过 | 启动 200，健康检查实例一致，停止后端口释放 |
| 真实出图端到端验收 | 未完成 | 不在本次边界内 |
