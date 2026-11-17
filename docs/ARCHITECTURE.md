# 技术架构与模块边界

## 1. 推荐初始技术路线

  -----------------------------------------------------------------------------------------------
  层                      技术                    职责
  ----------------------- ----------------------- -----------------------------------------------
  桌面容器                Tauri 2.x               Windows
                                                  窗口、应用生命周期、系统对话框、通知、sidecar
                                                  管理、安装包

  前端                    React + TypeScript +    中文桌面 UI、Prompt 编辑器、候选/草稿/历史/LoRA
                          Vite                    页面

  本地业务服务            Python 3.12 起步 +      领域逻辑、工作流解析/验证、LLM/ComfyUI
                          FastAPI                 适配、队列、数据访问

  Python 打包             PyInstaller             将 Python 服务和依赖打包为 Tauri 可启动的
                                                  Windows sidecar

  数据库                  SQLite                  本地结构化数据

  LLM                     Ollama 适配器（第一版） 发现模型、调用、停止、卸载、运行状态验证

  ComfyUI                 HTTP + WebSocket 适配器 工作流任务提交、事件、历史、队列状态与中断

  Windows 发布            Tauri Windows 安装程序  安装程序、快捷方式；安装后启动桌面应用
                          EXE                    
  -----------------------------------------------------------------------------------------------

**技术状态：** 这是推荐的初始架构基线，需在 M0 原型阶段验证 sidecar
启动、通信、打包和 Windows
安装体验后锁定具体版本。不要把未验证的版本号写成永久约束。

## 2. 选择理由

-   用户需要独立 Windows 桌面程序，同时希望界面具有网页技术的灵活性。
-   Tauri 使用系统 WebView2 渲染界面；Windows 11 通常具备 WebView2
    运行环境，可减少应用重复携带完整 Chromium 的负担。
-   Tauri 支持把外部可执行程序作为 sidecar；Python API 服务可以先用
    PyInstaller 打包，再由桌面应用管理其生命周期。
-   React/TypeScript 适合复杂 Prompt
    编辑器、结构化区块、差异对比和多页面状态管理。
-   Python 适合处理 JSON、HTTP/WebSocket、SQLite、本地模型服务和 ComfyUI
    集成。
-   将核心业务放在一个 Python 模块化单体中，避免把同一业务逻辑分散在
    TypeScript、Rust 和多个微服务。
-   Rust/Tauri 层保持轻薄，负责桌面宿主职责，不实现模型规则或 Prompt
    业务逻辑。

## 3. 进程与通信拓扑

### 桌面主进程（Tauri/Rust）

-   启动时拉起本应用 Python sidecar。
-   通过本地握手获取后端随机端口和会话凭据。
-   检查后端健康状态后再加载完整应用界面。
-   负责窗口、系统通知、文件选择对话框和 sidecar 生命周期。
-   退出时关闭本应用 sidecar；不得关闭 ComfyUI 或 Ollama 用户服务。

### 前端（React）

-   只通过本地后端 API 调用业务能力。
-   不直接读取/写入工作流文件，不直接连接 ComfyUI，不直接控制 Ollama
    进程。
-   对重要操作显示确认、差异和状态；不能把前端状态当作安全校验依据。

### 本地业务服务（Python）

-   只绑定 127.0.0.1，不监听 0.0.0.0。
-   使用随机可用端口和每次启动随机会话凭据；限制
    CORS/Origin；拒绝无会话凭据请求。
-   对输入做 schema 校验；对所有外部文件和研究资料视为不可信数据。
-   统一管理 SQLite、工作流解析、规则合并、LLM 任务、ComfyUI
    任务队列和生成历史。

### 外部服务

-   ComfyUI：用户自行启动；工作台连接用户配置的地址。
-   Ollama：用户自行安装/运行；工作台通过本地 API
    调用，不擅自杀掉服务进程。
-   NVIDIA 驱动/显存状态：按能力读取，无法确认时安全失败。

## 4. 目标目录结构

    /
      README.md
      package.json
      pnpm-lock.yaml
      vite.config.ts
      tsconfig.json
      src/
        app/
        components/
        features/
          workflows/
          prompt-studio/
          drafts/
          models/
          loras/
          queue/
          history/
          settings/
        services/
        styles/
      src-tauri/
        Cargo.toml
        tauri.conf.json
        capabilities/
        src/
      backend/
        pyproject.toml
        app/
          api/
          core/
          domain/
          services/
          adapters/
            comfyui/
            ollama/
            gpu/
          repositories/
          workflow/
          rules/
          prompt/
          queue/
          history/
        tests/
      docs/
      scripts/
      .github/workflows/

以上是目标结构，不代表这些目录或代码已经创建。

## 5. Python 后端模块边界

-   api：HTTP 路由、请求/响应模型、错误码；不放业务规则。
-   core：配置、日志、应用生命周期、异常类型。
-   domain：核心实体和值对象。
-   workflow：UI/API workflow 解析、节点识别、Prompt
    白名单、快照与差异验证。
-   rules：模型身份、规则导入、三级继承、优先级、冲突检测和动态检索。
-   prompt：创作任务构造、候选校验、翻译、区块、语法和 Token 检查。
-   adapters/ollama：模型发现、生成、停止、卸载和状态验证。
-   adapters/comfyui：连接、HTTP API、WebSocket、状态校准和任务提交。
-   adapters/gpu：显存与进程状态采集；能力不足必须报告 unknown。
-   queue：先进先出、暂停/恢复、取消、重试和崩溃恢复。
-   loras：元数据读取、角色卡、组合与工作流联动。
-   drafts：手动保存、版本历史、回收站和模型快照。
-   history：生成记录、文件路径状态、筛选和导出。
-   repositories：SQLite 数据访问和迁移。

## 6. 核心安全管线

1.  读取原始 workflow，不修改源文件。
2.  将 UI workflow 解析/转换为内部只读模型；提交前使用 API workflow。
3.  为当前工作流建立内容指纹和 Prompt 节点白名单。
4.  规则引擎只根据当前工作流实际模型组合选择规则。
5.  Prompt 生成输出进入候选，做 schema、术语、语法、正负向和规则检查。
6.  用户审核候选并明确确认写入。
7.  基于原始 API workflow 深拷贝，只修改白名单路径。
8.  对比原始快照和新快照；任何非白名单差异即拒绝。
9.  再次读取/校验工作副本；确认 Prompt 值准确，其他字段不变。
10. 入队前执行 LLM unload + 状态验证 + GPU memory verification。
11. 全部通过后才调用 ComfyUI 提交接口。
12. WebSocket 事件与 HTTP
    状态接口共同确认任务状态；未知状态不推断成功/失败。

## 7. ComfyUI 集成

-   第一版只支持一个 ComfyUI 实例，但地址、端口可配置。
-   使用 HTTP 接口提交 API workflow，接收 prompt_id。
-   使用 WebSocket 监听执行事件；通过 queue/history/status 接口校准。
-   支持断线重连、状态恢复、明确中断和手动重试。
-   ComfyUI 输出图片由 ComfyUI
    保存；工作台记录文件名、子目录、类型和解析后的路径。
-   输出目录从配置或 ComfyUI 返回数据确定，不写死某台电脑的路径。
-   工作台关闭不主动终止 ComfyUI 任务。

## 8. LLM 与显存策略

-   通过统一 LLM Runtime 接口隔离 Ollama
    细节，未来可扩展其他本地运行时。
-   第一版只实现 Ollama adapter，不下载模型。
-   生成期间只允许一个 LLM 任务。
-   出图前调用运行时卸载模型，并验证模型不再处于 loaded/running 列表。
-   同时读取 GPU
    显存状态；如果显存释放状态无法判断或仍高于安全阈值，阻止提交并解释。
-   不以"请求已发送"作为卸载成功；必须有可观察的状态证据。
-   阈值和验证方式需在真实设备上测量，不能在未测试前硬编码为保证值。

## 9. 数据存储原则

SQLite 数据库建议包含： - model_identities / model_files - model_rules /
rule_versions / rule_sources - workflows / workflow_recognition -
lora_cards / lora_files / lora_tags / lora_groups / lora_combinations -
drafts / draft_versions / draft_tags - generation_jobs /
generated_images - queue_items - app_settings / llm_profiles -
app_events / diagnostics

图片原件、模型权重和原始工作流不放进数据库；数据库只保存必要元数据、路径、索引和快照。关键
JSON 快照应记录 schema_version。

## 10. 错误处理与恢复

-   外部服务连接失败、超时、解析失败、未知状态均使用明确错误类型。
-   任务状态至少区分
    queued、preparing、running、succeeded、failed、interrupted、unknown、cancelled。
-   已提交任务不能因 WebSocket 短暂断开直接标失败。
-   应用异常退出后恢复持久化队列记录；不自动重出。
-   草稿未保存内容不做自动备份；只保证最后一次用户主动保存的版本。
-   数据库迁移先备份/校验；迁移失败不得静默破坏旧数据。

## 11. 测试策略

-   单元测试：规则继承、工作流识别、白名单差异、Prompt
    校验、状态机、队列。
-   属性/模糊测试：未知节点和任意非白名单字段不得被改动。
-   集成测试：ComfyUI mock server、Ollama mock server、SQLite
    临时数据库。
-   安全测试：伪造节点、未知字段、Prompt
    节点误识别、工作流变化、写入中断、回滚失败、LLM 卸载失败。
-   Windows 构建测试：sidecar
    启动、端口握手、安装/卸载、数据目录权限、桌面通知。
-   硬件验收：在用户 RTX 4060 Laptop 8GB + 16GB RAM
    环境验证真实显存释放与队列行为。

## 12. 打包与发布

-   开发态：Tauri dev server + Python 虚拟环境。
-   构建态：Python 后端用 PyInstaller 生成 Windows sidecar；Tauri 将
    sidecar 纳入应用包。
-   Windows 安装包优先生成 NSIS setup EXE；安装后创建快捷方式。
-   不把 Ollama 模型、ComfyUI、Checkpoint、LoRA
    或生成图片打包进安装程序。
-   WebView2 在 Windows 11 通常可用；安装器仍需配置合理的 WebView2
    检查/引导策略。
-   首版可先发布未签名测试包；正式公开分发前评估代码签名和更新机制。

## 13. 技术约束

-   模块化单体，不拆微服务。
-   Python 后端是业务逻辑唯一权威来源；前端只展示/发起命令。
-   Rust 层保持薄，不复制业务规则。
-   SQLite schema 迁移必须可追踪。
-   外部导入的模型资料不能作为可执行指令。
-   对无法确认的模型/节点/显存/任务状态保持 unknown，安全失败。
