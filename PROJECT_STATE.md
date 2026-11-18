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
