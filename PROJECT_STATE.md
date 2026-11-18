# PROJECT_STATE — 项目当前状态

- 任务编号：TASK-003.1-R2（状态回填）
- 记录日期：2026-11-18
- 记录人：豆包
- 状态口径：如实记录，计划中的功能一律不计为已完成；仅代码未验证的项明确标注“未验证”

## 1. 当前所处阶段

- 阶段：**M1/M2 工作流功能收尾**（M0 骨架与安全基线已完成；工作流导入/解析/白名单写入服务端测试通过，真机闭环待真实样本）。
- 当前任务：**TASK-003.1-R2** —— 工作流 API prompt 格式兼容与安全写入修正。
- 开发分支：`dev`，本地 = origin/dev `89aa48a18cf6f64278ab18500eb380a9856d61c0`；main `3084866aa85595133c7a1179b15ddd71e659d8f3` 未改、未合并。
- 版本：`0.1.0-dev.5`。
- **方向（ADR-0002，2026-11-18）**：免安装本机浏览器 Web 应用；默认 `http://127.0.0.1:17890`（原 8000 与本机酒馆冲突，已改），只绑定回环；不做 EXE/NSIS 安装包，不开发 Tauri/Rust 宿主。ADR-0001 旧路线已废弃，仅作历史记录。

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

## 11. TASK-003.1 工作流导入/解析/Prompt 白名单写入记录（2026-11-17，**未验收 / 未提交**）

### 11.1 当前状态

- 代码已按交付落盘到工作区，**未提交、未推送 dev**；起始 dev `9a76bdbc0bd3ef71a0f389f1782d8a6d13297e59`，main `3084866aa85595133c7a1179b15ddd71e659d8f3` 未改。
- 后端新增 API workflow 测试 6 项失败，真机闭环验收未执行；按口径不虚报通过。

### 11.2 已落盘文件

- 新增：`backend/workflow_service.py`、`backend/workflow_api.py`、`backend/test_workflow_service.py`、`frontend/src/WorkflowWorkbench.tsx`。
- 修改：`backend/main.py`（路由接入、版本 `0.1.0-dev.5`）、`frontend/src/App.tsx`（页面导航与切换）、`frontend/src/styles.css`（工作流样式）。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1/`（README、`Doubao-Receipt.md` 原始回执、known-issues、pytest-output、frontend-build）。

### 11.3 测试与构建

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| Python 编译检查 | 通过 | `py_compile` exit 0 |
| Python pytest | **51 passed / 6 failed** | 57 collected；既有 test_main 32、test_scripts 16 全过；新增 3 passed / 6 failed |
| TypeScript / Vite 构建 | 通过 | `tsc -b && vite build` exit 0，33 模块 |
| API workflow 解析/识别 | 未通过 | 6 个 API 用例在格式识别阶段被拒（见 11.4 P1） |
| 白名单写入 / 非白名单拒绝 / 指纹校验 | 未验证 | 导入阶段即失败，未走到写入链路 |
| 重启后导入记录持久化 | 未验证 | 真机闭环未执行 |
| UI workflow 浏览器只读 | 未验证 | 仅单元测试 `test_ui_workflow_is_parsed_but_not_writable` 通过 |
| 真实出图端到端验收 | 未完成 | 不在本次边界内 |

### 11.4 阻塞问题

- **P1（阻塞）**：`workflow_service.py` 的 `detect_format` / `_api_nodes` 从 `workflow["nodes"]` 取 API 节点；测试样本为 ComfyUI 标准扁平结构（根下直接是 `"1"…"6"`），无 `nodes` 键，抛 `WorkflowError: 无法识别工作流格式…`。待 ChatGPT 侧确认口径：① 解析器适配扁平 API prompt；② 样本改为 `nodes` 包裹结构。详见证据目录 `known-issues.md`。

### 11.5 证据归档规则（自本任务起固定）

- 每项任务档案统一在 `docs/TASK_EVIDENCE/TASK-xxx/`；`Doubao-Receipt.md` 保留完整原始回执，其他文件存测试原始结果、截图、日志、环境信息与代码差异作为佐证；证据与代码一起提交 dev。规则全文见 `docs/MAINTENANCE_AND_AGENT_HANDOFF.md` 第 5.1 节。

## 12. TASK-003.1-R2 修正版落地记录（2026-11-18 回填）

### 12.1 当前状态

- 修正版 `backend/workflow_service.py` 已入库 dev；R1 的 6 个 API 格式识别失败已消除。
- dev 提交链：`bddc82c`（fix(workflow)，18 文件 2203 插入）→ `798496f`（回执回填）→ `89aa48a`（补归档访问日志）。main 未变，工作区干净。

### 12.2 测试与构建（已实测）

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| Python pytest | 通过 | **57 passed, 1 warning in 6.80s**（Python 3.13.18 / pytest 8.4.2，exit 0） |
| TypeScript / Vite 构建 | 通过 | `tsc -b && vite build` exit 0，33 模块，Vite 5.4.21 |
| py_compile | 通过 | exit 0 |
| 真机页面加载 / 列表接口 | 通过 | Edge 访问工作台，服务已连接；`GET /api/workflows` 200（空列表） |
| 导入→识别确认→白名单写入→重开持久化 | **未闭环** | 本机与仓库无真实 ComfyUI API workflow JSON 样本，未伪造；服务端逻辑由 pytest 覆盖 |
| 真机角色/模型/LoRA 识别、UI 只读、快照校验 | 未验证 | 待真实样本闭环 |
| 真实出图端到端验收 | 未完成 | 不在本次边界内 |

### 12.3 遗留与待办

- 三类回归测试待补：兼容 `nodes` 字典结构识别、版本快照存旧文本断言、重复导入/重开持久化断言。
- service 已知改进点（详见 R2 `known-issues.md`）：指纹规范化偏严格、ConditioningCombine/中转节点 conditioning 追溯、结构化白名单 diff、测试缺口、工程分层。
- Python 3.12 兼容性未验证；显存阈值待真机测量。
- 下一步：提供真实 ComfyUI 导出的 API workflow JSON，完成 M1/M2 真机闭环，再进入 M3。

## 13. TASK-003.1-R3 服务收尾记录（2026-11-18）

### 13.1 当前状态

- 在 R2 基础上完成中转 conditioning 追溯修复、结构化白名单 diff 改造与回归用例补齐；后端 **62 passed**，前端构建 exit 0。
- 改动仅限 `backend/workflow_service.py` 与 `backend/test_workflow_service.py`；前端无代码改动。

### 13.2 测试与构建（已实测）

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| Python pytest | 通过 | **62 passed, 1 warning in 6.95s**（Python 3.13.18 / pytest 8.4.2，exit 0） |
| TypeScript / Vite 构建 | 通过 | `tsc -b && vite build` exit 0，33 模块，Vite 5.4.21 |
| `nodes` 字典结构识别 | 通过 | `test_detect_api_workflow_wrapped_in_nodes` |
| 中转 conditioning 追溯 | 通过 | `test_passthrough_conditioning_node_trace_continues_upstream` |
| 版本快照存旧文本 | 通过 | `test_version_snapshot_keeps_previous_prompt_text` |
| 重开持久化 | 通过 | `test_reimport_and_reopen_persists_across_store_instances` |
| 非白名单值变更拒绝 | 通过 | `test_structural_diff_rejects_non_whitelist_value_change` |
| 真机浏览器闭环 | **未闭环** | 仍缺真实 ComfyUI API workflow 样本 |

### 13.3 遗留与 backlog

- 指纹规范化偏严格（数字 1/1.0、浮点精度、空值空串、链接 slot 序号）本轮刻意未放宽，待真实样本确认口径后再改。
- 工程分层：模型节点硬编码清单可抽配置；并发写锁未加；前端 `**{filename}**` 星号纯文本未渲染。
- Python 3.12 兼容性未验证；显存阈值待真机测量。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R3/`。

## 14. TASK-003.1-R4 真实 UI 样本识别与服务对接（2026-11-18）

### 14.1 当前状态

- 用两份用户提供的真实 UI 格式样本在真机完成只读识别核对；补齐 UI 解析模型 / LoRA 节点的只读参数提取。后端 **63 passed**，前端构建 exit 0。
- Ollama（11434）与 ComfyUI（8188，0.30.2）经工作台 `/api/services/status` 探测均在线；样本 checkpoint / lora 名与 ComfyUI `object_info` 清单逐项核对存在。
- 改动仅限 `backend/workflow_service.py` 与 `backend/test_workflow_service.py`；前端无代码改动。

### 14.2 真机样本结果

| 样本 | 格式 | 节点 | Checkpoint | LoRA |
| --- | --- | --- | --- | --- |
| `silver_hair_2p5d_txt2img_workflow.json` | ui | 7 | `RH_Illustrious_2.5D_V1.safetensors` | 无 |
| `suyuexisdxl.json` | ui | 8 | `intorealismUltra_v80.safetensors` | `suyuexifull_c1-st6000.safetensors`，0.7 / 0.85 |

### 14.3 测试与构建（已实测）

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| Python pytest | 通过 | **63 passed, 1 warning in 2.87s**（Python 3.13.18 / pytest 8.4.2，exit 0） |
| TypeScript / Vite 构建 | 通过 | `tsc -b && vite build` exit 0，33 模块，Vite 5.4.21 |
| UI 加载器 / LoRA 参数提取 | 通过 | `test_ui_parser_reads_loader_and_lora_widget_values` |
| 真机浏览器识别 | 通过 | 两份样本在工作流工作区打开，角色 / 模型 / LoRA 识别一致 |
| API workflow 写入闭环 | **未闭环** | 两份样本均为 UI 格式，仍缺一份「导出 API 格式」样本 |

### 14.4 边界与 backlog

- 后端当前仅有连通性探测；Ollama 对话生成（M4）、ComfyUI 提交 / 队列 / 结果拉取 / 输出目录映射（M6）尚未实现。
- `storage.checkpoint`、`storage.lora` 仍为空串；外部模型目录扫描、身份缓存与输出目录索引属 M3 / M7 / M8。
- 指纹规范化偏严格、并发写锁、前端星号纯文本渲染、Python 3.12 兼容性、显存阈值等待既有 backlog 不变。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R4/`。

## 15. TASK-003.1-R5 真实 API 样本写入闭环（2026-11-18）

### 15.1 当前状态

- 用用户从 ComfyUI 导出的真实 API 格式样本 `suyuexisdxlapi.json`（8 节点）在真机跑通写入闭环：导入识别 → 白名单确认 → 写回工作副本 → 完整性校验 → 刷新重开持久化；原始文件未改，版本快照保存写入前版本。后端 **64 passed**，前端构建 exit 0。
- 本轮代码改动仅在 `backend/test_workflow_service.py` 补 1 条全链路回归用例；服务端解析/写入逻辑与前端无改动。

### 15.2 真机闭环结果

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| API 样本导入识别 | 通过 | 节点 1 Checkpoint `intorealismUltra_v80`；节点 10 LoRA `suyuexifull_c1-st6000` 0.7/0.85；正向 4、负向 5 |
| 白名单确认 | 通过 | 节点 4 正向、节点 5 负向，状态「已确认白名单」 |
| 写回与完整性校验 | 通过 | 1 个节点变化；非白名单字段校验通过；篡改 seed 被拒 |
| 刷新重开持久化 | 通过 | 重开后工作副本标记仍在，负向未变 |
| 原始文件与快照 | 通过 | `original.json` 未改；`versions/` 1 份写入前快照 |
| Python pytest | 通过 | **64 passed, 1 warning in 2.68s** |
| TypeScript / Vite 构建 | 通过 | `tsc -b && vite build` exit 0，33 模块 |

### 15.3 边界与 backlog

- 未向 ComfyUI 提交出图任务；队列/进度/结果拉取/输出目录索引属 M6，未实现。
- Ollama 对话生成（M4）、外部模型目录扫描与身份缓存（M3 / M8）未做。
- R4 `52d8d3a` 与本轮 R5 改动待网络恢复后推送远端 dev；本地已落盘。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R5/`。

## 16. TASK-003.1-R6 M3 第一切片：模型清单只读对接（2026-11-18）

### 16.1 当前状态

- M3「模型身份库与规则引擎」第一切片落地：从 ComfyUI `/object_info` 只读拉取 Checkpoint / CLIP / VAE / LoRA 在册清单，配置外部目录后做文件名存在性核对；未配置目录标记为未知（`null`），不臆测为缺失。本轮不复制、不哈希、不修改模型权重。
- 后端新增 `backend/model_catalog.py` 与 `backend/test_model_catalog.py`（5 例）；`backend/main.py` 新增 `GET /api/models/catalog`；前端设置页新增只读清单面板。后端 **69 passed**，前端构建 exit 0。

### 16.2 真机验收结果

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| 清单接口在线拉取 | 通过 | online=true；Checkpoint 13、CLIP 0、VAE 3、LoRA 3 |
| 分组正确 | 通过 | VAE 不混入 Checkpoint；见 `samples/catalog-summary.json` |
| 真实目录存在性核对 | 通过 | 指向 `models\checkpoints`、`models\loras`，13 ckpt / 3 lora 全部 `on_disk=true` |
| 未配置目录不臆测 | 通过 | `on_disk=null`，界面显示「目录未配置」；核对后设置恢复空串 |
| 浏览器渲染 | 通过 | `screenshots/model-catalog.png`、`model-catalog-list.png` |
| 未授权拦截 | 通过 | 未带会话访问接口返回 401（离线测试覆盖） |
| Python pytest | 通过 | **69 passed, 1 warning in 3.75s** |
| TypeScript / Vite 构建 | 通过 | `tsc -b && vite build` exit 0，33 模块 |

### 16.3 边界与 backlog

- 未实现 SHA256 身份库、三级规则继承、规则来源/可信度/版本/回退、冲突检测、动态检索、云端资料导入审核，均属后续 M3 切片。
- 目录索引只扫直下层权重文件，不递归子目录；存在性仅比对文件名，不读大小/哈希。
- Ollama 对话生成（M4）、ComfyUI 提交/队列/进度/结果/输出目录索引（M6）未实现。
- 停止脚本身份校验既有缺陷（`creation_date=null`、CIM 读取失败）未能自动回收；本轮手动核对身份后回收进程树，待后续修复。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R6/`。

## 17. TASK-003.1-R7 M3 第二切片：模型身份库骨架与元数据缓存（2026-11-18）

### 17.1 当前状态

- M3 第二切片落地：新增 `backend/model_identity.py`，SQLite `model_identity` 表按 `category + relative_name` 唯一记录绝对路径、大小、mtime、可空 SHA256 与时间戳；目录索引只扫直下层权重后缀；大小/mtime 变化使缓存哈希失效；SHA256 流式计算、按需触发并缓存，大 checkpoint 不 eager 哈希。
- `/api/models/catalog` 在已配置 checkpoint/lora 目录时索引身份库，并给每条清单回挂 `identity` 摘要（known / on_disk / size_bytes / sha256 / hashed）；无记录返回 `{known:false}`，不臆测。前端清单右侧标签由存在性改为身份摘要（大小 · 已校验/未哈希）。
- 后端新增 `backend/test_model_identity.py`（7 例），`test_model_catalog.py` 追加 1 例接口身份回挂；后端 **77 passed**，前端构建 exit 0。

### 17.2 真机验收结果

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| 身份摘要回挂 | 通过 | 配置真实目录后 13 ckpt / 3 lora 均 `known=true, on_disk=true`，带 `size_bytes`、`hashed=false`、`sha256=null` |
| 元数据大小正确 | 通过 | 样例 ckpt 6,938,041,288 字节（6.5 GB）；样例 lora 51,059,544 字节（48.7 MB） |
| 按需哈希并缓存 | 通过 | 最小 LoRA `suyuexi.safetensors`（37,866,968 字节）`ensure_hash` 后 `hashed=true`，摘要前缀 `fedeb940e772`；复调复用缓存 |
| 文件变更使哈希失效 | 通过 | 单元测试覆盖：size/mtime 变化后缓存 sha256 置空 |
| 浏览器渲染 | 通过 | `screenshots/identity-catalog.png`、`identity-catalog-list.png`；LoRA 已校验/未哈希标签区分 |
| 未配置目录不臆测 | 通过 | 核对后设置恢复空串；未记录条目 `{known:false}` |
| Python pytest | 通过 | **77 passed, 1 warning in 4.26s** |
| TypeScript / Vite 构建 | 通过 | `tsc -b && vite build` exit 0，33 模块 |

### 17.3 边界与 backlog

- 本轮只落身份库骨架与元数据缓存；架构/模型/Checkpoint 三级规则继承、规则来源/可信度/版本/回退、多模型与实际启用 LoRA 规则组合、冲突检测、动态检索、云端资料导入审核均属后续 M3 切片。
- 哈希为按需触发，尚无全量/定时哈希策略与前端触发入口；VAE/CLIP 目录本轮未进身份库索引。
- 目录索引只扫直下层权重文件，不递归子目录；并发写锁未加。
- Ollama 对话生成（M4）、ComfyUI 提交/队列/进度/结果/输出目录索引（M6）未实现。
- 停止脚本身份校验既有缺陷未修；证据：`docs/TASK_EVIDENCE/TASK-003.1-R7/`。

## 18. TASK-003.1-R8 M3 第三切片：同 SHA256 多路径身份归并（2026-11-18）

### 18.1 当前状态

- 在 R7 身份库骨架上补摘要归并：同类别下持有相同 SHA256 的多个文件映射到同一身份组；`identity_group` 返回 `identity_key`（`category:digest`）、`digest` 与副本列表；`identity_summary` 回挂 `identity_key`、`copy_count`、`copies`（相对名/绝对路径/在盘）。无摘要时身份键为 None，不做哈希推断。
- 后端测试增至 **80 passed**；前端类型补充副本字段，构建 exit 0。

### 18.2 真机验收结果

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| 同摘要归并 | 通过 | 单元测试：两份相同内容副本 `copy_count=2`、同一 `identity_key`；不同内容不归并 |
| 未哈希无身份键 | 通过 | 单元测试：无摘要 `identity_key=None`、`copies=[]` |
| 真机摘要回挂 | 通过 | `suyuexi.safetensors` 哈希后 `identity_key=lora:fedeb940…`，`copy_count=1`，见 `samples/merge-summary.json` |
| 浏览器渲染 | 通过 | `screenshots/identity-merge-list.png`；已校验/未哈希标签正常 |
| Python pytest | 通过 | **80 passed, 1 warning in 4.44s** |
| TypeScript / Vite 构建 | 通过 | `tsc -b && vite build` exit 0，33 模块 |

### 18.3 边界与 backlog

- 归并仅按类别内摘要匹配；跨类别同名/同摘要不合并。文件移动后按身份重新定位、多路径别名展示留后续切片。
- 规则继承、规则来源/可信度/版本/回退、规则组合与冲突检测、动态检索、云端资料导入审核仍属后续 M3 切片。
- 哈希按需触发，尚无全量/定时策略与前端触发入口；VAE/CLIP 目录未纳入索引；目录不递归；并发写锁未加。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R8/`。

## 19. TASK-003.1-R9 M3 第四切片：规则记录结构、三级继承与冲突/未知判定骨架（2026-11-18）

### 19.1 当前状态

- 新增 `backend/rule_engine.py` 纯解析层：`RuleRecord` 含层级（checkpoint/architecture/global）、作用域键、规则键、值、来源（provenance）、可信度（confidence）、版本与备注；`resolve_field` 按程序确定的优先级 checkpoint > architecture > global 逐级查找；同层值不一致标记 `conflict` 不替选；无覆盖字段标记 `unknown` 不造默认；`resolve_context` 批量解析并汇总冲突/未知；`summarize_rules` 按层级盘点。
- 本轮为纯函数层：不读文件系统、不调 ComfyUI/Ollama、不回写工作流；规则存储/导入、动态检索与 LLM 上下文组装留后续切片。
- 后端测试增至 **88 passed**；前端构建 exit 0（本轮无前端改动）。

### 19.2 验收结果

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| 三级继承优先级 | 通过 | 单元测试：checkpoint 覆盖 architecture/global；architecture 回落 global |
| 不跨上下文泄漏 | 通过 | 单元测试：checkpoint 规则不进入 architecture 上下文 |
| 同层冲突不替选 | 通过 | 单元测试：同层两值冲突返回 `conflict`、value=None、双来源 |
| 未知不造默认 | 通过 | 单元测试：无覆盖字段 `unknown`、source_level=None |
| 来源/可信度/版本保留 | 通过 | 解析结果回挂 source（level/scope/provenance/confidence/version/note） |
| 解析样本 | 通过 | `samples/rule-resolution.json`：steps=32（checkpoint）、cfg=7（global）、clip_skip=unknown |
| Python pytest | 通过 | **88 passed, 1 warning in 4.26s** |
| TypeScript / Vite 构建 | 通过 | `tsc -b && vite build` exit 0，33 模块 |

### 19.3 边界与 backlog

- 规则尚无持久化存储与资料导入；旧 `legacy-materials/profiles` 文本档案未结构化入库。
- 多模型与实际启用 LoRA 规则组合、冲突人工裁决界面、动态检索、云端研究资料导入审核未实现。
- 哈希按需触发；VAE/CLIP 目录未纳入索引；目录不递归；并发写锁未加。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R9/`。

## 20. TASK-003.1-R10 M3 第五切片：规则 SQLite 持久化与检索接口骨架（2026-11-18）

### 20.1 当前状态

- 新增 `backend/rule_store.py`：SQLite `workbench_rule` 表（level/scope_key/rule_key 唯一，value 以 JSON 存标量/列表/对象）；`upsert_rule`/`lookup_rule`/`list_rules`/`delete_rule`/`load_records`/`resolve_stored`；写入前交 `RuleRecord.validate()` 校验；装载为引擎记录后走三级继承解析。
- `main.py` 初始化规则表；新增只读接口 `GET /api/rules`（按 level/scope_key 过滤）与 `GET /api/rules/resolve`（按 level/scope_key/keys 解析，只解析请求键，冲突/未知如实上报，非法层级与空键返回 400）。
- `client` fixture 抽到 `backend/conftest.py` 供跨测试文件复用。后端测试增至 **98 passed**；前端构建 exit 0（本轮无前端改动）。

### 20.2 验收结果

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| 规则增查删与 JSON 往返 | 通过 | 单元测试：upsert 覆盖同三元组、列表值往返、按层级/作用域过滤、删除 |
| 非法记录入库前拒绝 | 通过 | 单元测试：非法层级抛 RuleError，未写库 |
| 存储规则接入引擎继承 | 通过 | 单元测试：三级记录解析 checkpoint=32、未知字段 unknown |
| 检索接口 | 通过 | 接口测试：`/api/rules` 清单、`/api/rules/resolve` 继承解析、空键/坏层级 400 |
| 真机冒烟 | 通过 | `samples/smoke-rules.json`：空清单 200；空规则未知字段全 unknown；坏层级/空键 400 |
| Python pytest | 通过 | **98 passed, 1 warning in 4.48s** |
| TypeScript / Vite 构建 | 通过 | `tsc -b && vite build` exit 0，33 模块 |

### 20.3 边界与 backlog

- 本轮只做持久化与只读检索；规则写入/导入接口、旧 profiles 文本结构化入库、前端规则管理界面未实现。
- 多模型与启用 LoRA 规则组合、冲突人工裁决界面、动态检索、LLM 上下文组装、版本/差异回退未实现。
- 哈希按需触发；VAE/CLIP 目录未纳入身份库索引；目录不递归；并发写锁未加；stopper 身份校验缺陷未修。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R10/`。

## 21. TASK-003.1-R11 M3 第六切片：规则写入/删除接口与会话 CSRF 保护（2026-11-18）

### 21.1 当前状态

- `main.py` 新增 `POST /api/rules`（upsert）与 `DELETE /api/rules`（按 level/scope_key/key 删除）；`RuleUpsert`/`RuleDelete` pydantic 模型限定键长与来源/可信度枚举由存储层二次校验；非法层级/记录返回 400，不写库。
- 写/删请求走既有本地会话与 CSRF 中间件（cookie 会话需 `X-Workbench-CSRF`，Bearer 测试调用豁免）。前端 `apiDelete` 方法补齐。
- 后端测试增至 **100 passed**；前端构建 exit 0。

### 21.2 验收结果

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| upsert 写入 | 通过 | 接口测试：POST 后清单 1 条，值/层级回挂正确 |
| 删除规则 | 通过 | 接口测试：DELETE 返回 removed=True，清单清空 |
| 非法记录拒绝 | 通过 | 接口测试：level=avatar 返回 400，未写库 |
| 真机写删闭环 | 通过 | `samples/smoke-rules-write.json`：写入→清单→解析 steps=32→非法 400→删除→清空 |
| Python pytest | 通过 | **100 passed, 1 warning in 4.70s** |
| TypeScript / Vite 构建 | 通过 | `tsc -b && vite build` exit 0，33 模块 |

### 21.3 边界与 backlog

- 本轮无前端规则管理界面；旧 profiles 文本结构化导入、多模型/LoRA 组合、冲突人工裁决、动态检索、LLM 上下文组装、版本/差异回退未实现。
- 哈希按需触发；VAE/CLIP 目录未纳入索引；目录不递归；并发写锁未加；stopper 身份校验缺陷未修。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R11/`。

## 22. TASK-003.1-R12 M3 第七切片：旧 profiles 文本解析器与来源/可信度标注映射（2026-11-18）

### 22.1 当前状态

- 新增 `backend/profile_parser.py`：纯只读解析层，把旧 `profiles/*.txt` 分节文本转成规则**候选**（`RuleCandidate` / `ParsedProfile`），不写库、不调 ComfyUI/Ollama、不回写工作流。
- 标注映射：`[已核实]/[镜像核实]` → verified_mirror/partial；`[作者说明]` → author/partial；`[作者推荐]/[作者示例]` → author/authoritative；含「社区」→ community/unverified；待核实/其余 → unverified/unverified。同时识别无方括号的前缀标签（作者推荐/作者示例/社区参考等）。
- 缺失口径：未给出/待填写/未找到/暂无/空值记为 unknown 字段，不产出候选；范例字段内嵌「未找到」同样判缺失；架构标签剥离尾部全角/半角括号备注。
- `candidates_to_records(profile, level, scope_key)` 把候选投影成规则记录形状的纯 dict（rule_key=`SECTION::Field`、version=`legacy-1`、带 source_section/source_raw），持久化留后续切片。
- 后端测试 **105 passed**；前端构建 exit 0。

### 22.2 验收结果

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| 身份字段提取 | 通过 | filename/display_name/architecture 顶层提取 |
| 缺失字段不产候选 | 通过 | unknown_fields 记录，候选清单不含缺失键 |
| 标注映射 | 通过 | 已核实/作者说明/作者推荐/社区四类映射正确 |
| 记录形状投影 | 通过 | `candidates_to_records` 输出 level/scope_key/rule_key/source_raw |
| 真实 13 份档案盘点 | 通过 | `samples/profile-parse-summary.json`：13 文件，288 候选，270 未知字段，全部解析出文件名 |
| Python pytest | 通过 | **105 passed, 1 warning in 4.76s** |
| TypeScript / Vite 构建 | 通过 | `tsc -b && vite build` exit 0，33 模块 |

### 22.3 边界与 backlog

- 本轮只产出候选与投影 dict；候选→规则库的审核导入流程、三级规则实际数据装载、前端规则管理界面未实现。
- 解析为保守口径：值内散文不作参数解析（步长/分辨率/CFG 保留原文）；哈希按需；VAE/CLIP 目录未索引；并发写锁未加；stopper 身份校验缺陷未修。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R12/`。

## 23. TASK-003.1-R13 M3 第八切片：旧档案扫描清单与候选预览只读接口（2026-11-18）

### 23.1 当前状态

- 新增 `backend/profile_source.py`：扫描 `legacy-materials/profiles/*.txt`（目录可由 `WORKBENCH_PROFILES_DIR` 覆盖，便于测试）；清单返回文件名/身份/架构/候选数/未知字段；损坏或不可读文件记 `error` 不抛 500。
- `main.py` 新增只读接口：`GET /api/profiles`（清单）、`GET /api/profiles/{file_name}`（单档案候选预览，404 处理）。预览复用 `candidates_to_records` 投影，**不写规则库**。
- 解析口径修正：IDENTITY 节只提取匹配身份（filename/display_name），不再产生规则候选。
- 后端测试 **109 passed**；前端构建 exit 0。

### 23.2 验收结果

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| 清单汇总 | 通过 | 接口测试：两份样本身份/架构/候选数/未知字段正确 |
| 候选预览 | 通过 | 接口测试：记录含 level/scope_key/rule_key/value/来源/可信度；预览后规则库为空 |
| 缺失档案 404 | 通过 | 接口测试：Missing.txt 返回 404 |
| 目录缺失容错 | 通过 | 接口测试：目录不存在返回空清单，不报错 |
| 真机闭环 | 通过 | `samples/smoke-profiles.json`：13 份清单、预览 11 候选、404、预览后入库 0 条 |
| Python pytest | 通过 | **109 passed, 1 warning in 4.79s** |
| TypeScript / Vite 构建 | 通过 | `tsc -b && vite build` exit 0，33 模块 |

### 23.3 边界与 backlog

- 本轮为只读预览：候选审核导入落库、三级规则实际数据装载、前端规则/档案管理界面未实现。
- 参数仍为原文散文；多模型/LoRA 组合、冲突裁决、动态检索、LLM 上下文装配、版本/差异回退未实现。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R13/`。

## 24. TASK-003.1-R14 M3 第九切片：档案候选审核导入规则库（2026-11-18）

### 24.1 当前状态

- `profile_source.py` 新增 `import_profile(connection, file_name)`：把单份档案候选导入为 **checkpoint 级**规则；每条落库前过引擎 `RuleRecord.validate()`，非法候选记入 `rejected` 不中断整批；无完整 checkpoint 文件名的档案 400 拒绝。
- `main.py` 新增 `POST /api/profiles/import`（`ProfileImport.file_name`），走既有本地会话与 CSRF 中间件；404 档案、400 无身份/非法记录分别处理。
- 导入报告返回 `imported` 条数、`rejected` 明细、`unknown_fields`。
- 后端测试 **112 passed**；前端构建 exit 0。

### 24.2 验收结果

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| 导入落库 | 通过 | 接口测试：Alpha 档案 2 条 checkpoint 规则入库，清单可见 |
| 引擎校验 | 通过 | 非法候选跳过记 rejected；无文件名档案 400 |
| 解析回读 | 通过 | 接口测试：入库 Steps=20 经引擎 resolve 为 resolved |
| 缺失档案 404 | 通过 | 接口测试：Nope.txt 返回 404 |
| 真机闭环 | 通过 | `samples/smoke-import.json`：Anything_V5 导入 11 条、0 拒绝、解析回读、清理归零 |
| Python pytest | 通过 | **112 passed, 1 warning in 5.08s** |
| TypeScript / Vite 构建 | 通过 | `tsc -b && vite build` exit 0，33 模块 |

### 24.3 边界与 backlog

- 本轮仅 checkpoint 级导入；architecture/global 级规则装载、参数结构化拆分、前端导入/审核界面未实现。
- 导入为整档 upsert，无逐候选勾选/驳回/差异预览；多模型/LoRA 组合、冲突人工裁决、动态检索、LLM 上下文装配、版本/差异回退未实现。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R14/`。

## 25. TASK-003.1-R15 M3 第十切片：生成参数值结构化解析（2026-11-18）

### 25.1 当前状态

- 新增 `value_normalize.py` 纯函数层：步数/CFG/Clip Skip 解析为 `value`/`range`/`floor`；分辨率解析为 `resolutions` 列表；采样器/调度器解析为 `list`。解析失败保留原文，`structured=None`，不臆测数值。
- `profile_parser.candidates_to_records` 每条记录附 `structured`；`rule_store` 表新增 `structured_json` 列（旧库 `ALTER TABLE` 补列），`value_json` 仍存原始裸值，不破坏引擎 `record.value` 原样返回口径。
- `import_profile` 透传候选 `structured` 落库；回读记录同时给出 `value`（原文）与 `structured`（可比较结构）。
- 后端测试 **118 passed**；前端构建 exit 0。

### 25.2 验收结果

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| 数值/范围解析 | 通过 | 单值 `7`→value；`6~12`/`1.5~2`→range；`30+`→floor；非数值回退 None |
| 分辨率/列表 | 通过 | `896×1152 / 832×1216`→resolutions；多采样器→list |
| 失败回退 | 通过 | 散文值（如「SDXL 友好分辨率」「待核实」）structured=None，原文保留 |
| 落库回读 | 通过 | 真机 IntoRealism 导入 16 条，Steps/CFG/Resolution/Sampler 结构化正确回读，清理归零 |
| Python pytest | 通过 | **118 passed, 1 warning in 5.36s** |
| TypeScript / Vite 构建 | 通过 | `tsc -b && vite build` exit 0，33 模块 |

### 25.3 边界与 backlog

- 结构化仅覆盖生成参数六类字段；提示词/标签/架构等散文字段不拆。
- 结构尚未被前端展示或用于参数比对/冲突检测；architecture/global 级装载、逐候选审核界面、多模型/LoRA 组合、动态检索、LLM 上下文装配、版本/差异回退仍未实现。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R15/`。

## 26. TASK-003.1-R16 M3 第十一切片：架构级规则随档案导入（2026-11-18）

### 26.1 当前状态

- 候选投影按分节分流：`ARCHITECTURE` 节事实落 **architecture** 级，scope_key 为解析出的底座标签（如 `SD1.5`/`SDXL 1.0`）；其余节落 **checkpoint** 级，scope_key 为完整 checkpoint 文件名。
- 无底座标签的架构字段无法确定作用域，导入时记入 `rejected`，不擅自归到 checkpoint 或全局；引擎层级/继承/冲突口径不变。
- 导入接口按记录自带的 `level`/`scope_key` 落库，复用既有校验与结构化落库链路。
- 后端测试 **119 passed**；前端构建 exit 0。

### 26.2 验收结果

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| 架构级分流 | 通过 | 接口测试：Base Architecture/Model Type 落 architecture 级 scope=SDXL 1.0；Steps 落 checkpoint 级 |
| 无底座标签拒绝 | 通过 | 无 Base Architecture 的 Model Type 记入 rejected，Steps 正常入库 |
| 作用域隔离 | 通过 | checkpoint 上下文解析架构字段为 unknown，架构规则不泄漏进 checkpoint 作用域 |
| 真机闭环 | 通过 | `samples/smoke-levels.json`：Anything_V5 导入 11 条，9 checkpoint + 2 architecture(SD1.5)，清理归零 |
| Python pytest | 通过 | **119 passed, 1 warning in 5.23s** |
| TypeScript / Vite 构建 | 通过 | `tsc -b && vite build` exit 0，33 模块 |

### 26.3 边界与 backlog

- 本轮不装载 global 级规则：旧档案中暂无跨模型通用事实的来源，全局规则留后续明确来源后再建。
- 架构标签为档案散文标签，未做归一化/同义归并（如 SD1.5 与 sd1.5）；架构级规则的前端展示、跨模型继承在真机上下文装配时再验。
- 逐候选勾选/驳回/差异预览、多模型/LoRA 组合、冲突人工裁决、动态检索、LLM 上下文装配、版本/差异回退仍未实现。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R16/`。

## 27. TASK-003.1-R17 M3 第十二切片：工作流 checkpoint 规则上下文检索（2026-11-18）

### 27.1 当前状态

- 新增 `rule_store.context_for_checkpoint()`：按完整 checkpoint 文件名精确匹配 checkpoint 规则；经底座标签关联架构级规则；附全局规则；不相关 checkpoint 规则不进入上下文。
- 新增 `GET /api/workflows/{id}/rules`：从工作流分析结果取首个 checkpoint 文件名（`ckpt_name`/`unet_name`），返回该上下文相关规则；未识别 checkpoint 或未登记模型返回 `unregistered`，空规则集，不臆造。
- 架构关联兼容 Base Architecture 事实已被分流到架构级的情形；引擎三级继承/冲突/未知口径不变。
- 后端测试 **122 passed**；前端构建 exit 0。

### 27.2 验收结果

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| checkpoint 精确匹配 | 通过 | 接口测试：sample_checkpoint 规则入上下文，other_checkpoint 规则被排除 |
| 架构级关联 | 通过 | 上下文 architecture=SD1.5，带回 Model Type 等架构规则 |
| 未登记不臆造 | 通过 | 未知 checkpoint 与无 checkpoint 工作流均返回 unregistered、空规则集 |
| 真机闭环 | 通过 | `samples/smoke-context.json`：intorealismUltra_v80 上下文 14 checkpoint + 2 architecture(SDXL 1.0)；ghost 未注册；清理归零 |
| Python pytest | 通过 | **122 passed, 1 warning in 5.52s** |
| TypeScript / Vite 构建 | 通过 | `tsc -b && vite build` exit 0，33 模块 |

### 27.3 边界与 backlog

- 本轮仅按 checkpoint 匹配；启用 LoRA 的规则组合尚未纳入（旧档案无 LoRA 规则来源）。
- 上下文只做规则归集，尚未装配成发给 LLM 的裁剪提示；冲突人工裁决界面、动态检索、版本/差异回退、前端规则/档案管理界面未实现。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R17/`。

## 28. TASK-003.1-R18 M3 第十三切片：上下文规则装配为 LLM 裁剪提示（2026-11-18）

### 28.1 当前状态

- 新增 `rule_prompt.build_prompt_context()`：把 R17 上下文规则经引擎 checkpoint → architecture → global 继承解析，装配为可下发的裁剪提示载荷；每字段保留来源层级、来源、可信度与版本。
- 新增 `GET /api/workflows/{id}/rules/prompt`：注册模型返回解析后字段集、冲突/未知列表与说明指令；未识别/未登记模型返回空字段集与「不得猜测」指令。
- 引擎 `resolve_field`/`resolve_context` 增加可选 `architecture_scope`，显式区分 checkpoint 作用域与架构家族作用域。
- 后端测试 **127 passed**；前端构建 exit 0。

### 28.2 验收结果

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| 继承优先级程序确定 | 通过 | 测试：checkpoint Steps 覆盖架构/全局；架构与全局字段各自标注来源层级 |
| 冲突/未知不由 LLM 猜测 | 通过 | 同层冲突保留 conflict 与双来源；未覆盖字段入 unknown；未注册空载荷 |
| 来源/可信度随字段保留 | 通过 | 真机 Steps=6~12，source=checkpoint，confidence=authoritative |
| 真机闭环 | 通过 | `samples/smoke-prompt.json`：16 字段（14 checkpoint + 2 architecture/SDXL 1.0），0 冲突；ghost 未注册；清理归零 |
| Python pytest | 通过 | **127 passed, 1 warning in 5.52s** |
| TypeScript / Vite 构建 | 通过 | `tsc -b && vite build` exit 0 |

### 28.3 边界与 backlog

- 本轮只装配载荷，不调用 Ollama、不发送提示、不回写工作流（M4 接入）。
- 启用 LoRA 规则组合、冲突人工裁决界面、上下文裁剪长度控制与动态检索未实现。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R18/`。

## 29. TASK-003.1-R19 M3 第十四切片：结构化规则值与工作流实际参数保守比对（2026-11-18）

### 29.1 当前状态

- 采样器组报告补充 `params` 快照（steps/cfg/sampler_name/scheduler/denoise 标量），API 与 UI 两种解析均提取。
- 新增 `rule_compare.py` 纯函数层：规则结构化值（range/floor/value/resolutions/list）与工作流实际参数保守比对；可判定给 `match`/`out_of_range`/`out_of_set`，不可判定归 `unknown`（实际非数值、规则未结构化、字段不可比、规则冲突/未知）。
- 新增 `GET /api/workflows/{id}/rules/compare`：返回逐字段比对、实际值与计数；未注册工作流空比对集。
- 后端测试 **137 passed**；前端构建 exit 0。

### 29.2 验收结果

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| 数值范围/下限/单值比对 | 通过 | 单测：range 命中/越界、floor 命中/越界、value 相等判定 |
| 列表集合比对 | 通过 | 单测：采样器名大小写归一后命中/不在集合 |
| 不可判定不臆造 | 通过 | 非数值实际、未结构化规则、冲突规则、非参数字段均 unknown |
| 真机闭环 | 通过 | `samples/smoke-compare.json`：Steps 35→out_of_range(6~12)、CFG 5.5→out_of_range(1.5~2)、Sampler→out_of_set；Scheduler 带备注未结构化→unknown；清理归零 |
| Python pytest | 通过 | **137 passed, 1 warning in 5.81s** |
| TypeScript / Vite 构建 | 通过 | `tsc -b && vite build` exit 0 |

### 29.3 边界与 backlog

- 比对只读，不回写工作流、不触发 LLM；VAE/CLIP 参数未纳入比对。
- 带备注数值（如 Scheduler `Karras（Euler A 时）`）仍回退原文、structured=None，比对归 unknown。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R19/`。

## 30. TASK-003.1-R20 M3 第十五切片：架构标签归一化与同家族规则归并（2026-11-18）

### 30.1 当前状态

- 新增 `architecture_normalize.py` 纯函数层：把同义变体（`SDXL`/`SDXL 1.0`/`sdxl`）归到规范家族；混合/派生标签标 `mixed`，不强行并入纯家族；未识别标签留 `other`，不猜家族。
- 规则上下文按规范家族归并架构规则：同一家族不同原始标签的架构规则都纳入上下文；混合标签不继承纯家族规则。
- 导入时在 checkpoint 桶补 `IDENTITY::Base Architecture` 身份指针，保留该模型底座标签原值；未登记模型不再从其他模型架构桶回退标签。
- 提示载荷透传 `architecture_family` 与 `architecture_label`。
- 后端测试 **147 passed**；前端构建 exit 0。

### 30.2 验收结果

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| 同义变体归并 | 通过 | 单测：`SDXL`/`SDXL 1.0`/`sdxl` 同家族；SD1.5、Pony 各自独立 |
| 混合/派生不并入 | 通过 | 单测：`Pony / SDXL 系` mixed；`Illustrious SDXL 系` mixed；`微调自 IL-XL` 留 other |
| 同家族规则归并 | 通过 | 单测：SDXL 1.0 上下文纳入 SDXL 与 SDXL 1.0 两个 scope，排除 SD1.5；混合标签不并入纯 SDXL |
| 未登记不猜家族 | 通过 | 未登记 checkpoint 上下文 `architecture`/`family` 均为 None |
| 真机闭环 | 通过 | `samples/smoke-normalize.json`：intorealismUltra（SDXL 1.0）family=SDXL，纳入 SDXL + SDXL 1.0，排除 Pony / SDXL 系；清理归零 |
| Python pytest | 通过 | **147 passed, 1 warning in 5.79s** |
| TypeScript / Vite 构建 | 通过 | `tsc -b && vite build` exit 0 |

### 30.3 边界与 backlog

- 归一化仅识别 SD1.5/SDXL/Pony 三个明确家族；其余标签留 other，待证据补充后再扩映射。
- 架构规则继承仍按家族整体继承；家族内冲突人工裁决界面未实现。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R20/`。

## 31. TASK-003.1-R21 M3 第十六切片：参数值剥离尾部备注后再结构化解析（2026-11-18）

### 31.1 当前状态

- 结构化解析前剥离尾部中文/英文括号备注（适用条件、示例说明）；清洗副本走现有 normalizer，`raw` 保留原值可追溯。
- Sampler/Scheduler 单值归为单元素列表；分号分隔的两套建议不混并，仍留 unstructured。
- 后端测试 **151 passed**；前端构建 exit 0。

### 31.2 验收结果

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| 尾部备注剥离 | 通过 | 单测：`25（使用指南参考…）`→value 25；`Karras（Euler A 时）`→list ["Karras"]；raw 保留原值 |
| 单值列表 | 通过 | 单测：`LCM`→单元素 list |
| 两套建议不混并 | 通过 | 单测：`35；25~40`→structured=None |
| 比对链路 | 通过 | 单测：剥离备注后的 Scheduler 规则与实际 karras 命中 match |
| 真机闭环 | 通过 | `samples/smoke-notes.json`：Scheduler 结构化 list ["Karras"] 并 resolved；Steps/CFG/Sampler 保持；清理归零 |
| Python pytest | 通过 | **151 passed, 1 warning in 5.88s** |
| TypeScript / Vite 构建 | 通过 | `tsc -b && vite build` exit 0 |

### 31.3 边界与 backlog

- 仅剥离**尾部**括号；括号内含关键参数、分号第二套建议不在本轮拆分。
- 多套建议（示例/指南并存）的分组结构化、Resolution 与 latent 尺寸对接在后续切片。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R21/`。

## 32. TASK-003.1-R22 M3 第十七切片：Resolution 规则对接实际 latent 尺寸比对（2026-11-18）

### 32.1 当前状态

- 解析层识别 `EmptyLatentImage` 等 LatentImage 节点，提取 width/height 标量写入报告 `latent`（API/UI 两段路径一致）。
- 比对 actuals 注入 latent 宽高；Resolution 规则（structured kind=`resolutions`）与实际 (宽,高) 整数集合保守匹配：集合内 match，否则 out_of_set；缺宽/高或非数值归 unknown。
- 后端测试 **156 passed**；前端构建 exit 0。

### 32.2 验收结果

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| latent 尺寸提取 | 通过 | 单测：API 样本提取 832×1216；无 latent 节点报告 latent=None |
| actuals 注入宽高 | 通过 | 接口测试：compare actuals 带 width=704 / height=1024 |
| Resolution 集合匹配 | 通过 | 单测：命中 match；不命中 out_of_set；缺尺寸 unknown/actual_missing |
| 真机闭环 | 通过 | `samples/smoke-resolution.json`：latent 704×1024；规则 {896×1152, 832×1216} 判 out_of_set；清理归零 |
| Python pytest | 通过 | **156 passed, 1 warning in 5.75s** |
| TypeScript / Vite 构建 | 通过 | `tsc -b && vite build` exit 0 |

### 32.3 边界与 backlog

- 仅取首个有效 latent 节点；多采样器组逐组比对、多 latent 节点取舍在后续切片。
- 括号内分辨率提取、分号两套建议分组结构化仍未实现；散文型 Resolution（如「SDXL 友好分辨率」）structured=None，保持 unknown。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R22/`。

## 33. TASK-003.1-R23 M3 第十八切片：Resolution 解析保留括号内尺寸（2026-11-18）

### 33.1 当前状态

- Resolution 字段直接在原始文本上提取 `W×H`（含括号备注内的尺寸），不再被尾部备注剥离误伤；重复尺寸按首次出现去重。
- 数值/列表字段维持 R21 口径：先剥离尾部括号备注再解析，`raw` 保留原值。
- 后端测试 **158 passed**；前端构建 exit 0。

### 33.2 验收结果

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| 括号内尺寸提取 | 通过 | 单测：`（768×1152 / 648×1152 / 864×1152，待核对 V3）`→resolutions 三项 |
| 重复尺寸去重 | 通过 | 单测：`832×1216 / 832×1216`→单元素 |
| 数值字段备注剥离不受影响 | 通过 | 真机：Clip Skip `2（非 V3 独立参数）`→value 2；Steps `30~32` range |
| 真机闭环 | 通过 | `samples/smoke-res-paren.json`：Resolution 三组尺寸结构化；清理归零 |
| Python pytest | 通过 | **158 passed, 1 warning in 5.81s** |
| TypeScript / Vite 构建 | 通过 | `tsc -b && vite build` exit 0 |

### 33.3 边界与 backlog

- 分号两套建议（示例/指南）仍未分组结构化；散文型 Resolution（无任何 `W×H`）structured=None，保持 unknown。
- 括号内非尺寸备注（待核对、版本说明）仍保留在 `raw`，不参与结构化。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R23/`。

## 34. TASK-003.1-R24 M3 第十九切片：Clip Skip 实际参数链路（2026-11-18）

### 34.1 当前状态

- 解析层识别 `CLIPSetLastLayer` 节点，读取 `stop_at_clip_layer`（负停止层数），派生正数 `clip_skip` 写入报告；非负/非整数不换算，留 None。
- 比对 actuals 注入派生 `clip_skip`；Clip Skip 规则按数值路径比对；缺实际值归 unknown/actual_missing，非数值归 actual_not_numeric。
- 后端测试 **163 passed**；前端构建 exit 0。

### 34.2 验收结果

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| Clip Skip 派生 | 通过 | 单测：`stop_at_clip_layer=-2`→clip_skip 2；无节点 None；非负值 None |
| actuals 注入 | 通过 | 接口测试：compare actuals `clip_skip=2` |
| 数值比对 | 通过 | 单测：值 2 命中 match；1 判 out_of_range；缺失 unknown/actual_missing |
| 真机闭环 | 通过 | `samples/smoke-clip-skip.json`：规则 2 与实际 -2 派生 2 判 match；清理归零 |
| Python pytest | 通过 | **163 passed, 1 warning in 5.87s** |
| TypeScript / Vite 构建 | 通过 | `tsc -b && vite build` exit 0 |

### 34.3 边界与 backlog

- 仅取首个 CLIPSetLastLayer 节点；符号换算固定为 `clip_skip = -stop_at_clip_layer`（节点取值域 -24…-1），非标准值不猜。
- 真机暂无原生含该节点的工作流样本，本轮闭环基于构造 API 样本；多 CLIP 链路与双 CLIP 模型的跳过层数取舍未实现。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R24/`。

## 35. TASK-003.1-R25 M3 第二十切片：多采样器组 actuals 保守标注（2026-11-18）

### 35.1 当前状态

- `_sampler_actuals` 遍历全部采样器组，actuals 顶层仍取首个有参数的组；新增 `sampler_group_count` 与 `sampler_groups`（每组 node_id + params 摘要）。
- 多组参数不合并、不替选；逐组比对在后续切片。
- 后端测试 **164 passed**；前端构建 exit 0。

### 35.2 验收结果

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| 多组标注 | 通过 | 单测：双组样本顶层 steps=20，`sampler_groups` 含 20/30 两组 |
| 真机闭环 | 通过 | `samples/smoke-multi-groups.json`：count=2，首组 25/7.0，次组 30/6.0；清理归零 |
| Python pytest | 通过 | **164 passed, 1 warning in 5.87s** |
| TypeScript / Vite 构建 | 通过 | `tsc -b && vite build` exit 0 |

### 35.3 边界与 backlog

- 逐采样器组独立比对、组间参数冲突提示未实现；当前判定仅对应首组。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R25/`。

## 36. TASK-003.1-R26 M3 第二十一切片：前端规则比对结果只读展示（2026-11-18）

### 36.1 当前状态

- 工作流详情新增「规则与参数比对（只读）」面板：拉取 `/api/workflows/{id}/rules/compare`，展示注册状态、Checkpoint、架构、计数徽标、实际参数摘要与逐条比对条目（规则值 / 实际值 / 状态 / 理由）。
- 纯只读：不做规则勾选驳回、不写入规则库；unknown 条目原样展示理由。
- 后端测试 **164 passed**；前端 `tsc -b && vite build` exit 0。

### 36.2 验收结果

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| 面板渲染 | 通过 | `screenshots/compare-panel-meta.png`：已登记、checkpoint、架构 Pony / SDXL 系、计数 18/2、摘要步数 25 / CFG 7 / Clip Skip 2 / 832×1216 |
| 比对条目 | 通过 | `screenshots/compare-entries.png`：Clip Skip 2=2 匹配、Steps 25=25 匹配，其余 unknown 带理由 |
| 载荷样本 | 通过 | `samples/compare-payload.json`：counts `{unknown:18, match:2}` |
| Python pytest | 通过 | **164 passed, 1 warning in 6.14s** |
| TypeScript / Vite 构建 | 通过 | exit 0；`index-BUphuMzW.js 158.94 kB` |

### 36.3 边界与 backlog

- 未实现规则候选勾选/驳回、差异预览、冲突人工裁决入口；当前面板只展示后端比对结论。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R26/`。

## 37. TASK-003.1-R27 M3 第二十二切片：多采样器组逐组比对（2026-11-18）

### 37.1 当前状态

- 后端 `compare_workflow` 在顶层首组结论之外，新增 `sampler_group_comparisons`：每个采样器组用公共事实（latent 尺寸、Clip Skip）叠加本组 params 独立比对，返回节点 id、params、逐条结论与分组计数；组间不合并不替选。
- 前端比对面板在多组工作流下展开「逐采样器组比对」小节，逐组卡片展示节点、参数摘要、分组计数与条目结论；顶层结论仍对应首组。
- 后端测试 **164 passed**；前端 `tsc -b && vite build` exit 0。

### 37.2 验收结果

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| 逐组比对 | 通过 | 组 7（steps 25 / cfg 7.0）Steps 匹配；组 9（steps 30 / cfg 6.0）Steps 超出范围；分组计数独立 |
| 前端分组卡片 | 通过 | `screenshots/compare-group1.png`、`compare-group2.png`；载荷 `samples/compare-payload.json` |
| Python pytest | 通过 | **164 passed, 1 warning in 6.03s** |
| TypeScript / Vite 构建 | 通过 | exit 0；`index-DX9kN6tt.js 160.40 kB` |

### 37.3 边界与 backlog

- 多组间参数冲突只逐组呈现，未做跨组冲突裁决或推荐取值。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R27/`。

## 38. TASK-003.1-R28 M3 第二十三切片：规则库只读清单界面（2026-11-18）

### 38.1 当前状态

- 服务与设置页新增「规则库（只读）」面板，拉取 `GET /api/rules`，按 checkpoint / architecture / global 三级分组展示规则键、作用域、原始值、结构化摘要、来源、可信度、版本与备注。
- 纯只读：不提供新增、修改、删除入口；空库显示「规则库为空」。
- 后端测试 **164 passed**；前端 `tsc -b && vite build` exit 0。

### 38.2 验收结果

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| 规则分组展示 | 通过 | 模型档案 15 条、架构基线 5 条；`screenshots/rules-checkpoint-group.png`、`rules-architecture-group.png` |
| 载荷样本 | 通过 | `samples/rules-payload.json`：20 条，architecture 5 / checkpoint 15 |
| Python pytest | 通过 | **164 passed, 1 warning in 6.15s** |
| TypeScript / Vite 构建 | 通过 | exit 0；`index-8q4qtSIr.js 161.93 kB` |

### 38.3 边界与 backlog

- 规则新增/编辑/删除、档案候选审核导入入口仍在后端接口层，前端未开放写操作。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R28/`。

## 39. TASK-003.1-R29 M3 第二十四切片：多 latent/CLIP 节点保守标注（2026-11-18）

### 39.1 当前状态

- `workflow_service.py` 的 API/UI 两段解析在保留顶层 `latent`、`clip_skip`（取首个节点）的同时，新增 `latent_nodes`、`clip_skip_nodes` 全量列表；多节点不合并、不替选，其余节点如实列出。
- `workflow_api._sampler_actuals` 透传 `latent_node_count`/`latent_nodes`、`clip_skip_node_count`/`clip_skip_nodes`；比对结论仍对应首节点。
- 前端比对面板在摘要区对多节点给出保守提示：结论取首个，其余节点未参与比对。
- 后端测试 **165 passed**；前端 `tsc -b && vite build` exit 0。

### 39.2 验收结果

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| 多 latent 列表 | 通过 | 节点 6（832×1216）、10（768×1152）；顶层取节点 6；`samples/compare-payload.json` |
| 多 CLIP 跳过层列表 | 通过 | 节点 8（clip_skip 2）、11（clip_skip 3）；顶层取节点 8 |
| 前端多节点提示 | 通过 | `screenshots/compare-multi-nodes.png`：两条「结论取首个；其余节点未参与比对」提示 |
| 比对结论 | 通过 | registered；计数 无法判定 17 / 匹配 2 / 不在集合 1；Clip Skip 2=2、Steps 25=25 匹配 |
| Python pytest | 通过 | **165 passed, 1 warning in 6.03s** |
| TypeScript / Vite 构建 | 通过 | exit 0；`index-BaTB97FZ.js 162.27 kB` |

### 39.3 边界与 backlog

- 多 latent / 多 CLIP 链路目前只标注事实并取首节点比对；逐节点取舍、跨节点冲突裁决与逐节点比对留后续切片。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R29/`。

## 40. TASK-003.1-R30 M3 第二十五切片：旧档案候选只读预览界面（2026-11-18）

### 40.1 当前状态

- 设置页新增「旧档案候选（只读）」面板：首载并行拉取 `GET /api/profiles`，按档案展示完整 checkpoint 文件名、识别架构、候选数、未识别字段数。
- 点击档案行展开，懒加载 `GET /api/profiles/{file}`，嵌套列出候选规则的层级、作用域、原始值、结构化摘要、备注、来源/可信度/版本标签。
- 纯只读对接既有后端；不提供导入、勾选、驳回等任何写控件；后端零改动。
- 后端测试 **165 passed**；前端 `tsc -b && vite build` exit 0。

### 40.2 验收结果

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| 档案清单 | 通过 | 13 份旧档案全部列出；`samples/profiles-payload.json` |
| 候选预览展开 | 通过 | 展开 Anything_V5：12 条候选，层级/作用域/值/备注/来源可信度标签齐全；`screenshots/profile-preview.png` |
| 只读口径 | 通过 | 面板无导入/勾选/驳回按钮；本轮规则表保持 0 条 |
| Python pytest | 通过 | **165 passed, 1 warning in 6.10s** |
| TypeScript / Vite 构建 | 通过 | exit 0；`index-Cw2T345o.js 164.26 kB`，CSS 8.09 kB |

### 40.3 边界与 backlog

- 档案候选的勾选/驳回/差异预览与前端规则、档案管理写界面留后续切片；本切片仅只读预览。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R30/`。

## 41. TASK-003.1-R31 M3 第二十六切片：结构化规则值前端可读摘要（2026-11-18）

### 41.1 当前状态

- 新增共享工具 `frontend/src/format.ts`：`formatStructured` 按 kind 渲染 value/range/floor/resolutions/list 可读摘要；`formatActual` 兼容比对 verdict 提炼值（数值、范围、下限、分辨率对/数组、列表数组）。
- 规则库、档案候选面板的 `structured` 字段与比对面板规则列改用共享格式化；未知形态回退原始 JSON，`structured=None` 显示「—」。
- 纯展示层改动，后端归一化与比对结论口径不变；后端零改动。
- 后端测试 **165 passed**；前端 `tsc -b && vite build` exit 0。

### 41.2 验收结果

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| value / range / floor 摘要 | 通过 | CFG 5、Steps 30~32、CFG 4~6、Steps ≥30；`screenshots/rules-summary.png` |
| resolutions / list 摘要 | 通过 | `896×1152 / 832×1216`、采样器以 `/` 连接 |
| 比对面板规则列 | 通过 | 数值/分辨率/列表/下限摘要正确；`screenshots/compare-summary.png`；`samples/compare-payload.json` |
| Python pytest | 通过 | **165 passed, 1 warning in 6.04s** |
| TypeScript / Vite 构建 | 通过 | exit 0；`index-D68eGJQw.js 165.08 kB`，CSS 8.09 kB |

### 41.3 边界与 backlog

- 分号两套建议的分组结构化与示例套/推荐套优先级语义留后续切片；本切片摘要只服务既有 kind。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R31/`。

## 42. TASK-003.1-R32 M3 第二十七切片：前端星号 markdown 残留清理（2026-11-18）

### 42.1 当前状态

- 工作流识别结果标题行 `**{filename}**` 字面 markdown 星号改为 `<strong>` 加粗标签，与左侧列表项范式一致。
- 全前端 `.tsx` 复查无其他 markdown 标记残留；纯前端展示修复，后端零改动。
- 后端测试 **165 passed**；前端 `tsc -b && vite build` exit 0。

### 42.2 验收结果

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| 标题行文件名加粗、无字面星号 | 通过 | `screenshots/title-bold.png` |
| 全前端无其他 markdown 残留 | 通过 | 检索确认 |
| Python pytest | 通过 | **165 passed, 1 warning in 6.14s** |
| TypeScript / Vite 构建 | 通过 | exit 0；`index-Bgw4pSpK.js 165.10 kB`，CSS 8.09 kB |

### 42.3 边界与 backlog

- 无功能性遗留；既有 backlog 沿用 R31 清单。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R32/`。

## 43. TASK-003.1-R33 M3 第二十八切片：分号两套建议分组结构化（sets，保守归 unknown）（2026-11-18）

### 43.1 当前状态

- 归一化层按分号拆套：两套均可解析时产出 `sets` 分组结构；任一子套失败整体 `structured=None`，不混并示例套与推荐套。
- 列表归一化识别缺失标记（未给出/待核实/待填写/未找到/暂无/none/no），不把缺失文案提升为推荐项。
- 比对层 `sets` 暂归 `unknown / structured_kind_unhandled`，不做命中判定；前端摘要递归渲染各套。
- 后端测试 **168 passed**；前端 `tsc -b && vite build` exit 0。

### 43.2 验收结果

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| 双套数值/范围/分辨率/采样器分组 sets | 通过 | Steps `35；25~40`、CFG `4；4~6`；`samples/rules-payload.json` |
| 缺失标记套整体归 None | 通过 | Scheduler `Exponential；未给出` |
| 比对层 sets 归 unknown 无误判 | 通过 | `structured_kind_unhandled`；`samples/compare-payload.json` |
| 前端 sets 摘要渲染 | 通过 | `screenshots/rules-sets.png` |
| Python pytest | 通过 | **168 passed, 1 warning in 6.16s** |
| TypeScript / Vite 构建 | 通过 | exit 0；`index-BK2qO8n_.js 165.17 kB`，CSS 8.09 kB |

### 43.3 边界与 backlog

- 示例套/推荐套优先级语义未拍板；sets 判定留后续切片。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R33/`。

## 44. TASK-003.1-R34 M3 第二十九切片：VAE/CLIP 目录只读核对链路（2026-11-18）

### 44.1 当前状态

- catalog 的 CLIP/VAE 名称接入与 Checkpoint/LoRA 同一套只读目录存在性核对；配置目录才逐项判命中/未找到，未配置目录 `on_disk=None`（未知，不报未找到）。
- `datadir` 外部目录白名单扩为 `checkpoint/lora/clip/vae`，默认 storage 补两个空串键；前端存储标签与清单网格补 CLIP 列。
- 不进身份哈希库、不拷贝权重、不算摘要；`_annotate` 修正空的已配置目录不再被误判为未知。
- 后端测试 **169 passed**；前端 `tsc -b && vite build` exit 0。

### 44.2 验收结果

| 验收项 | 状态 | 证据 / 说明 |
| --- | --- | --- |
| CLIP/VAE 目录核对链路接入 | 通过 | `fetch_catalog` 补 `clip_dir`/`vae_dir`；单测覆盖命中/未找到/未知 |
| 未配置目录 on_disk=None 不回归 | 通过 | 真机 Checkpoint 13 / LoRA 3 / VAE 3 全部 `None`；`samples/catalog-payload.json` |
| 前端 CLIP 列与外部目录标签 | 通过 | `screenshots/catalog-four-columns.png` |
| Python pytest | 通过 | **169 passed, 1 warning in 6.34s** |
| TypeScript / Vite 构建 | 通过 | exit 0；`index-DJeMbr87.js 165.64 kB`，CSS 8.09 kB |

### 44.3 边界与 backlog

- CLIP/VAE 未进身份哈希索引；无大小/摘要/校验标注，不参与身份归并。
- 目录索引不递归子文件夹；真机未配置 CLIP/VAE 目录，命中分支由临时目录单测覆盖。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R34/`。

## 45. TASK-003.1-R35 CLIP/VAE 接入身份索引与摘要挂载（2026-11-18，批量终验节奏首批）

### 45.1 落地内容

- catalog 端点目录索引、摘要构建、identity 回填三段循环合并为统一 `identity_groups`，
  扩入 `clip`/`vae`；CLIP/VAE 沿用与 Checkpoint/LoRA 同一套身份库：按需哈希、不 eager、
  文件 size/mtime 变化使缓存失效，无摘要不推断身份。
- 前端 CLIP/VAE 清单条目由 `diskLabel` 改为统一 `identityLabel`；身份未命中时回退磁盘标签，
  保守口径不变。
- 新增端点单测：配置临时 clip/vae 目录后，两条目 `identity.known=True`、`on_disk=True`、
  大小与磁盘一致。
- 后端测试 **170 passed**；前端 `tsc -b && vite build` exit 0（`index-CPKxdkMV.js 165.62 kB`）。

### 45.2 边界与 backlog

- CLIP/VAE 哈希仍按需触发，无全量/定时哈希策略与前端哈希触发入口。
- 真机未配置 CLIP/VAE 目录，命中分支由临时目录单测覆盖；本批按批量终验节奏，真机验收在阶段收口统一进行。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R35/`。

## 46. TASK-003.1-R36 M4 第一切片：Ollama 模型只读发现（2026-11-18）

### 46.1 落地内容

- 新增 `GET /api/ollama/models`：读取本地 Ollama `/api/tags`，返回 `{online, models:[name], error}`。
- 离线、超时、响应非 JSON 或结构不符时保守返回 `online=False`、空列表与错误信息；不切云端、不臆造模型名。
- 新增单测：端点透传在线清单、透传离线状态；辅助函数直连不可达地址返回保守空结果。
- 后端测试 **173 passed**；本批无前端改动。

### 46.2 边界与 backlog

- 模型选择/参数配置、候选生成、结构化验证、审核前不写入工作流等 M4 主体功能留后续切片。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R36/`。

## 47. TASK-003.1-R37 M4 第二切片：本地 Ollama 候选生成后端闭环（2026-11-18）

### 47.1 落地内容

- 新增 `llm_client.py`：本地 Ollama `/api/chat` 非流式调用；离线/超时/坏 JSON/空消息保守返回
  `ok=False`，无云端回退、不臆造候选文本。
- 新增 `POST /api/workflows/{id}/prompt/candidates`：复用规则上下文构建 system/user 消息，
  只传当前工作流相关规则；返回 `{model, candidates:[text], rule_status, conflicts, unknown}`。
- 候选不回写工作流，working draft 保持不变；本地模型失败返回 502 `{online:False, error}`；
  模型名去空白后不能为空（422）。
- 新增单测：成功返回候选且草稿不变、无关规则不进消息；本地失败 502；空模型 422。
- 后端测试 **176 passed**；本批无前端改动。

### 47.2 边界与 backlog

- 前端模型选择、候选展示、审核后写入工作流、三种创作模式与参数配置、输出结构化验证留后续切片。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R37/`。

## 48. TASK-003.1-R38 M4 第三切片：前端模型选择与候选审核闭环（2026-11-18）

### 48.1 落地内容

- 工作区新增“本地模型候选”面板：拉取 `/api/ollama/models` 填充模型下拉，可选填任务要求，
  调 `POST /api/workflows/{id}/prompt/candidates` 生成候选。
- 候选文本只读展示；“采用到正向 Prompt”仅填入正向编辑框，不自动写工作副本；落库仍走既有
  确认白名单 + 审核写入链路。
- 本地 Ollama 离线或无模型时给出保守提示，不臆造候选。
- 后端测试 **176 passed**；前端 `tsc -b && vite build` exit 0（`index-B7xvjVEX.js 167.20 kB`）。

### 48.2 边界与 backlog

- 三种创作模式、模型参数配置、输出结构化验证、候选多版本对比留后续切片。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R38/`。

## 49. TASK-003.1-R39 M6 第一切片：ComfyUI 设备与显存状态只读解析（2026-11-18）

### 49.1 落地内容

- 新增 `fetch_comfyui_status(url)`：只读拉取 `/system_stats`，提取 ComfyUI 版本、PyTorch 版本、
  内存总量/空闲与各设备（索引/名称/类型/显存总量/空闲）。
- 新增 `GET /api/comfyui/status`；离线、超时、坏 JSON 或结构不符保守返回 `online=False`、字段
  `None`、设备空列表，不臆测数值；不提交任务、不控制 ComfyUI 进程。
- 数值字段经非负整数校验，布尔/负数/非数值回退 `None`；非字典设备条目跳过。
- 新增 4 个单测：端点透传、离线透传、不可达主机保守容错、混合类型结构解析容错。
- 后端测试 **180 passed**；本批无前端改动。

### 49.2 边界与 backlog

- 队列先进先出、暂停/恢复/取消/重试、任务 HTTP 提交、WebSocket 进度、断线恢复、显存与 LLM
  卸载互斥判断留后续切片。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R39/`。

## 50. TASK-003.1-R40 M6 第二切片：队列与历史只读探测（2026-11-18）

### 50.1 落地内容

- 新增 `fetch_comfyui_queue(url)`：只读拉取 `/queue`（运行中/待执行）与 `/history`，仅投影
  prompt 标识；不提交、不取消、不调整队列顺序。
- 新增 `GET /api/comfyui/queue`；离线、超时、坏 JSON 或结构不符保守返回空列表与错误，不臆造 id。
- 新增 4 个单测：端点透传、离线透传、不可达主机容错、混合类型标识解析容错。
- 后端测试 **184 passed**；本批无前端改动。

### 50.2 边界与 backlog

- 任务 HTTP 提交、提交前显存/LLM 卸载闸门、WebSocket 进度订阅、断线恢复与中断任务不自动重出
  留后续切片。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R40/`。

## 51. TASK-003.1-R41 M6 第三切片：任务提交后端与本地记录（2026-11-18）

### 51.1 落地内容

- 新增 `backend/comfy_client.py`：标准库 urllib 的只读探测（`comfyui_online`、
  `loaded_ollama_models` 读 `/api/ps`）与受控提交 `submit_prompt`（POST `/prompt`）；无云端回退，
  离线/超时/坏 JSON/缺 prompt_id/非空 node_errors 一律保守失败。
- 新增 `backend/comfy_tasks.py`：`comfy_task` 表持久化提交记录（prompt_id、workflow_id、status、
  时间戳、node_errors、last_error、outputs）；状态枚举 submitted/running/succeeded/failed/
  interrupted/unknown；失败不自动重出。
- `workflow_service.read_working()` 读取工作副本；`workflow_api` 新增
  `POST /api/workflows/{id}/tasks` 与 `GET /api/workflows/{id}/tasks`。
- 提交闸门 fail-closed：ComfyUI 不可达 502；UI 格式 400；白名单未确认 400；Ollama 不可达（无法
  确认卸载）502；LLM 仍驻留 409；提交失败 502 且不写本地记录。
- 新增 8 个单测：未确认拒绝、UI 格式拒绝、ComfyUI 离线、Ollama 离线、LLM 驻留、成功落库并回读、
  节点错误不落库、未知工作流 404。后端测试 **192 passed**。

### 51.2 边界与 backlog

- 显存具体阈值、Ollama 卸载与出图互斥的放宽口径未拍板，本批只做"无法确认即拒绝"，不设数值门槛。
- 队列先进先出/暂停/恢复/取消/重试、WebSocket 进度订阅、queue/history 回读状态校准、断线恢复、
  中断任务不自动重出的界面与通知留后续切片。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R41/`。

## 52. TASK-003.1-R42 M6 第四切片：任务状态回读校准（2026-11-18）

### 52.1 落地内容

- `comfy_client.fetch_task_states`：聚合 `/queue` 运行中/待执行与 `/history` 详情（status_str、
  completed、outputs）；离线 fail-closed 空投影。
- `comfy_tasks.classify_history_status`：历史条目保守映射 succeeded/failed/interrupted/unknown，
  未明确报告成功/失败不臆造。
- `GET /api/workflows/{id}/tasks?refresh=true`：按 prompt_id 校准本地记录；队列/历史均找不到的在途
  任务记 unknown；ComfyUI 离线保留本地状态并返回 `sync_error`；不自动重出。
- 新增 5 个单测：历史成功、队列运行中、双找不到记 unknown、离线保留本地状态、状态分类纯函数。
- 后端测试 **197 passed**。

### 52.2 边界与 backlog

- WebSocket 进度订阅、队列暂停/恢复/取消/重试、断线恢复状态机、中断任务界面与通知留后续切片。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R42/`。

## 53. TASK-003.1-R43 M6 第五切片：前端任务面板（2026-11-18）

### 53.1 落地内容

- `WorkflowWorkbench.tsx` 新增 ComfyUI 任务面板：提交按钮（仅 API 格式且白名单已确认可用）、
  任务列表（状态徽章、prompt_id、提交时间、last_error、输出文件名）、刷新状态按钮（`?refresh=true`
  回读校准）、离线校准提示。
- 状态标签：待运行/运行中/已完成/失败/已中断/未知；UI 格式工作流提示不可直接提交。
- 打开/导入工作流时加载本地任务；提交成功后自动刷新校准。
- 前端 `tsc -b && vite build` 绿（`index-CTtb3PIL.js 169.24 kB gzip 54.36 kB`）；后端 **197 passed**。

### 53.2 边界与 backlog

- WebSocket 实时进度、队列暂停/恢复/取消/重试、断线恢复状态机、中断任务通知与图库视图留后续切片。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R43/`。

## 54. TASK-003.1-R44 M6 第六切片：任务取消与中断（2026-11-18）

### 54.1 落地内容

- `comfy_client.cancel_pending`（POST `/queue` `{"delete":[prompt_id]}`）与
  `interrupt_running`（POST `/interrupt` `{"prompt_id":...}`），接口形状核对自真机 ComfyUI 0.30.2
  `server.py`。
- `POST /api/workflows/{id}/tasks/{prompt_id}/cancel`：按本地状态路由；终态（succeeded/failed/
  interrupted）与 unknown 拒绝 409；ComfyUI 离线 502；远端失败不改本地记录；成功记 interrupted。
- 前端任务项对 submitted/running 提供取消/中断按钮，操作后刷新校准。
- 新增 6 个单测：待执行出队、运行中定向中断、终态拒绝、unknown 拒绝、离线状态不变、未知任务 404。
- 后端 **203 passed**；前端 `tsc -b && vite build` 绿（`index-CGPpLaRC.js 169.61 kB gzip 54.44 kB`）。

### 54.2 边界与 backlog

- 队列暂停/恢复、失败重试、WebSocket 实时进度、断线恢复状态机、通知与图库视图留后续切片。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R44/`。

## 55. TASK-003.1-R45 M6 第七切片：LLM/ComfyUI 互斥反向闸门（2026-11-18）

### 55.1 落地内容

- `comfy_client.queue_has_active_task`：在线且 running/pending 非空记 active；离线记
  `online=False, active=False`（离线不可能持有在途任务，不阻断）。
- `POST /api/workflows/{id}/prompt/candidates` 调本地 LLM 前先查队列：有在途任务 409 拒绝加载；
  队列空闲或 ComfyUI 离线放行。
- 新增 3 个单测：队列活动拒绝且不调 chat、空闲放行、离线放行。后端 **206 passed**。

### 55.2 边界与 backlog

- 显存数值阈值、Ollama 主动 unload 接口、WebSocket 进度、队列暂停/恢复/重试、断线恢复留后续切片。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R45/`。

## 56. TASK-003.1-R46 M7 第一切片：生成历史快照与图片索引（2026-11-18）

### 56.1 落地内容

- 新模块 `generation_history.py`：`generation_history` 表，提交时刻固化正向/负向 Prompt 文本与
  checkpoint/LoRA/VAE/CLIP 文件名快照；校准终态回写任务状态与图片文件名索引。
- 图片只记录 `filename/subfolder/type` 元数据，`exists` 留空（输出目录配置未接入，不臆造存在）；
  不复制原图，原图仍由 ComfyUI 输出目录管理。
- 只读端点 `GET /api/history`（可按 `workflow_id` 过滤）、`GET /api/history/{prompt_id}`。
- 新增 6 个单测：快照固化、快照不随后续草稿改动、成功回写图片、工作流过滤与 404、outputs 两种
  形状兼容、空报告保守空快照。后端 **212 passed**。

### 56.2 边界与 backlog

- 图片磁盘存在性探测（需 ComfyUI 输出目录配置）、时间轴/图库双视图、搜索筛选导出、历史反向创建
  草稿、缩略图索引留后续切片。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R46/`。

## 57. TASK-003.1-R47 历史图片存在性标注（2026-11-18）

### 57.1 落地内容

- `settings.storage` 新增可选外部目录 `output`（ComfyUI 输出目录，与 checkpoint/lora/clip/vae 同范式，
  可留空）；`datadir.OPTIONAL_EXTERNAL_KEYS` 与默认设置同步纳入。
- `generation_history.annotate_exists`：按输出目录 + 子目录 + 文件名核对 `exists`；未配置目录记
  `None`，文件存在 `True`、丢失 `False`；路径越出输出目录按丢失处理，不复制原图。
- 历史列表/详情端点返回时实时标注存在性；文件丢失历史记录保留，仅标记不存在。
- 新增 3 个单测：存在/丢失标注、未配置目录记 None、路径越出拒绝。后端 **215 passed**。

### 57.2 边界与 backlog

- 缩略图索引、时间轴/图库双视图、搜索筛选导出、历史反向创建草稿留后续切片。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R47/`。

## 58. TASK-003.1-R48 前端生成历史只读面板（2026-11-18）

### 58.1 落地内容

- 新增 `HistoryPanel.tsx`：导航「生成历史」页，只读列表展示提交时间、任务状态徽章、正向摘要、
  checkpoint/LoRA 名与图片存在标记；展开详情查看完整正/负向 Prompt、模型快照（Checkpoint/LoRA/
  VAE/CLIP）与输出图片清单。
- `App.tsx` 接入第三个导航页；图片存在性沿用后端 `exists`（存在/丢失/目录未配置），不复制原图。
- 前端 `tsc -b && vite build` 绿（`index-BHp-6yRK.js 172.58 kB gzip 55.14 kB`）。后端本批无改动，
  保持 215 passed。

### 58.2 阶段真机只读验收

- 启动后端（17890），只读端点全部 200：Ollama/ComfyUI 在线，ComfyUI 1 设备 vram_free≈7.45GB、
  队列空，Ollama 两模型，清单 13/0/3/3，历史空、规则 0。
- 真机样本导入解析正确（8 节点、1 checkpoint、1 LoRA 0.7/0.85、正/负 Prompt）；设置页、工作流
  识别页、历史空态三页截图留档。未真实提交出图。
- 验收后回收后端进程树（PID 20260 + 子进程 14760），端口关闭；规则/历史表归零，本次副本已清理。

### 58.3 边界与 backlog

- 缩略图索引、图库网格视图、历史反向创建草稿留后续切片。
- userdata/workflows 残留 22 个历次验收副本（非本轮新增），待确认后批量清理。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R48/`。

## 59. TASK-003.1-R49 历史记录筛选（2026-11-18）

### 59.1 落地内容

- 后端 `list_history` 增加 `status`（任务状态精确匹配）、`keyword`（大小写不敏感，匹配正/负向
  Prompt 文本与冻结模型快照文件名）只读过滤；`/api/history` 透传 `status`/`keyword` 查询参数。
  未知状态不重映射，匹配为空；LIKE 通配符转义。
- 前端 `HistoryPanel` 加状态下拉、工作流下拉（从现有记录派生）、关键词输入框，本地即时筛选；
  无匹配显示独立空态。
- 后端 **216 passed, 1 warning**；前端 `tsc -b && vite build` 绿（`index-B1NYoJeQ.js 173.69 kB
  gzip 55.39 kB`）。

### 59.2 边界与 backlog

- 缩略图索引、图库网格视图、按日期范围/导出、历史反向创建草稿留后续切片。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R49/`。

## 60. TASK-003.1-R50 失败/中断任务手动重试（2026-11-18）

### 60.1 落地内容

- 后端抽出 `_submit_guarded` 共享 fail-closed 提交闸门（ComfyUI 在线、API 格式、白名单确认、
  本地 LLM 已卸载确认）；首次提交与手动重试复用同一闸门。
- 新增 `POST /api/workflows/{id}/tasks/{prompt_id}/retry`：仅 `failed`/`interrupted` 可重试，
  succeeded/在途/unknown 拒绝 409；旧记录与历史快照保留，重试生成新 prompt_id 与新快照；
  远端失败不改旧记录、不自动重试。
- 前端任务面板对失败/已中断项提供「重试」按钮，成功后刷新任务列表。
- 后端 **220 passed, 1 warning**；前端 `tsc -b && vite build` 绿（`index-CClNSCnw.js 173.99 kB
  gzip 55.45 kB`）。

### 60.2 边界与 backlog

- WebSocket 实时进度、队列暂停/恢复、通知、Ollama unload 状态与显存阈值验证留后续切片。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R50/`。

## 61. TASK-003.1-R51 历史记录当前筛选结果导出 JSON（2026-11-18）

### 61.1 落地内容

- 历史面板加「导出 JSON」按钮，将当前状态/工作流/关键词筛选后的记录整体导出为本地 JSON
  （`workbench-history-<时间戳>.json`），含导出时间、条数与完整记录；仅记录文件名与存在性，
  不复制原图。纯前端 Blob 下载，无新增后端端点。
- 前端 `tsc -b && vite build` 绿（`index-DHO60mp6.js 174.51 kB gzip 55.66 kB`）；后端无改动，
  沿用 220 passed 基线。

### 61.2 边界与 backlog

- 缩略图索引、图库网格视图、日期范围导出、历史反向创建草稿留后续切片。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R51/`。

## 62. TASK-003.1-R52 只读诊断报告（2026-11-18）

### 62.1 落地内容

- 后端新增 `GET /api/diagnostics`：只读汇总应用/版本、Python/平台、数据域计数（规则、历史、
  任务、模型身份、工作流、档案）、托管与外部存储目录存在性、本地 Ollama/ComfyUI 可达性；
  数据库异常记入 `database_error` 而不中断报告；报告 `uploaded: false`，不含模型权重、原图或
  完整 Prompt 载荷。
- 前端设置页加「导出诊断报告」按钮，经前端 Blob 下载为本地 JSON，默认不上传。
- 后端 **221 passed, 1 warning**；前端 `tsc -b && vite build` 绿（`index-BCj7cW2p.js
  175.03 kB gzip 55.81 kB`）。

### 62.2 边界与 backlog

- 备份/恢复、数据库迁移、崩溃恢复与完整性检查、手动更新检查留后续切片。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R52/`。

## 63. TASK-003.1-R53 历史列表/网格双视图（2026-11-18）

### 63.1 落地内容

- 历史面板加列表/网格视图切换；网格以三列卡片展示摘要、状态、时间与模型，点击复用既有详情
  展开；响应式降为两列/单列。纯前端，无新增后端端点。
- 前端 `tsc -b && vite build` 绿（`index-XhKZQ7-1.js 175.20 kB gzip 55.89 kB`）；后端无改动，
  沿用 221 passed 基线。

### 63.2 边界与 backlog

- 缩略图索引、时间轴视图、日期范围导出、历史反向创建草稿留后续切片。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R53/`。

## 64. TASK-003.1-R54 版本快照只读列表（2026-11-18）

### 64.1 落地内容

- 后端 `WorkflowStore.list_versions(workflow_id)`：扫描 `versions/*.json` 快照按文件名时间戳
  降序，按白名单提取各快照正/负 Prompt 文本；损坏快照保守跳过；不提供恢复动作。
- 新增只读端点 `GET /api/workflows/{id}/versions`，返回 `{"items": [...]}`；未知工作流 404。
- 前端工作流详情面板新增「历史版本（只读）」小节，展示版本时间与正/负 Prompt 摘要，
  无恢复/差异按钮。
- 后端 **224 passed, 1 warning**；前端 `tsc -b && vite build` 绿
  （`index-vwJ__kjB.js 176.08 kB gzip 56.11 kB`）。

### 64.2 边界与 backlog

- 版本恢复、差异比对、备注、标签收藏、多草稿与草稿箱留后续切片；当前仅只读列表。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R54/`。

## 65. TASK-003.1-R55 设置只读导出 JSON（2026-11-18）

### 65.1 落地内容

- 前端设置页新增「导出设置」按钮：将当前已加载设置按白名单（`version/storage/connections`）
  经 Blob 下载 `workbench-settings-<时间戳>.json`；不含模型权重、原图、历史记录或遗留杂项。
- 纯前端，复用既有 `GET /api/settings` 数据；无新增后端端点。
- 后端沿用 **224 passed, 1 warning**；前端 `tsc -b && vite build` 绿
  （`index-lDUuS2TQ.js 176.57 kB gzip 56.19 kB`）。

### 65.2 边界与 backlog

- 设置导入、备份恢复整库、数据库迁移留后续切片；当前仅只读导出当前配置。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R55/`。

## 66. TASK-003.1-R56 历史日期范围筛选（2026-11-18）

### 66.1 落地内容

- 历史面板在状态/工作流/关键词筛选基础上，新增开始/结束日期本地即时筛选，按 `created_at`
  日期部分比较；纯前端，无新增后端端点。
- 后端沿用 **224 passed, 1 warning**；前端 `tsc -b && vite build` 绿
  （`index-Df9yT-1_.js 176.90 kB gzip 56.26 kB`）。

### 66.2 边界与 backlog

- 缩略图索引、时间轴视图、历史反向创建草稿留后续切片；日期范围仅本地过滤当前已加载记录。
- 证据：`docs/TASK_EVIDENCE/TASK-003.1-R56/`。
