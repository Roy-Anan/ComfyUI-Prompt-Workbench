# ComfyUI Prompt Workbench

一个面向 Windows 的本地 ComfyUI Prompt 创作与管理工作台。它使用本地 LLM
辅助编写、优化和管理图像生成提示词，并通过严格的白名单机制，把审核后的正向/负向
Prompt 写入 ComfyUI 工作流。

> **当前状态：文档基线包。** 需求梳理已完成（用户确认决策
> 01---132）；桌面产品方向已确定；本压缩包不包含已实现的软件代码，也不代表
> EXE 已经构建。

## 项目目标

在一个 Windows 桌面工作台中完成：

选择工作流 → 识别模型与提示词节点 → 按模型规则创作 Prompt → 用户审核 →
安全写入 → 卸载本地 LLM 并确认显存释放 → 提交 ComfyUI → 记录生成历史。

## 不可破坏的原则

1.  **工作流只允许修改用户确认的正向/负向 Prompt 白名单字段。**
    其他节点、参数、连接、Seed、尺寸、CFG、Steps、LoRA
    权重等必须保持不变。
2.  Prompt 先进入候选与审核流程；用户确认后才写入工作副本/任务数据。
3.  写入前后都做结构化差异检查；任何非白名单变化都拒绝提交。
4.  出图前必须完成本地 LLM 卸载与显存释放验证；无法确认时禁止提交。
5.  默认本地优先：不自动上传
    Prompt、草稿、图片或模型资料；第一版不接云端 AI API。
6.  草稿只在用户主动点击保存时持久化；生成历史自动记录。
7.  ComfyUI 由用户自行启动和关闭；工作台只连接和管理任务，不擅自控制
    ComfyUI 进程。
8.  原始工作流文件默认不覆盖；使用独立工作副本。

## 技术方向

-   Windows 桌面应用，最终交付安装程序 EXE。
-   网页技术构建 UI。
-   推荐初始方案：Tauri 2 + React + TypeScript + Vite + Python
    本地服务 + SQLite。
-   本地 LLM 第一版通过 Ollama 适配器接入。
-   ComfyUI 通过 HTTP + WebSocket 连接。
-   采用模块化单体，不拆微服务。

**注意：**
技术组合是当前推荐基线。工程启动阶段仍需做最小可运行原型，验证 Tauri 与
Python sidecar 的启动、通信、打包和 Windows 运行情况后，再冻结依赖版本。

## 文档导航

-   [项目介绍](docs/PROJECT_OVERVIEW.md)
-   [已确认需求基线](docs/REQUIREMENTS_BASELINE.md)
-   [技术架构](docs/ARCHITECTURE.md)
-   [开发路线图](docs/ROADMAP.md)
-   [维护与智能体交接手册](docs/MAINTENANCE_AND_AGENT_HANDOFF.md)
-   [ADR-0001 技术选型决策](docs/decisions/ADR-0001-TECH-STACK.md)
-   [上传到 GitHub 的操作说明](UPLOAD_GUIDE.md)

## 用户设备参考

-   Windows 11
-   Intel Core i7-12650H
-   16GB DDR4 3200 MT/s
-   NVIDIA RTX 4060 Laptop GPU，8GB VRAM
-   ComfyUI
    秋叶整合包；实际安装路径、监听地址和输出目录必须运行时读取或配置，不得写死
-   用户此前使用过 Ollama；新项目需运行时检测，不假定旧模型一定仍安装

工作台应使用独立 Python 环境/打包运行时，不复用 ComfyUI 内部 Python
环境，避免依赖冲突。

## 当前阶段

  阶段                     状态
  ------------------------ --------------------------------
  需求梳理                 已完成（决策 01---132 已确认）
  产品与架构文档           本压缩包已整理，待上传仓库
  技术原型验证             待开始
  工程脚手架               待建立
  工作流解析与白名单保护   待开发
  模型规则引擎             待开发
  Prompt 工作区与 LLM      待开发
  队列、显存调度、历史     待开发
  LoRA 管理                待开发
  UI 视觉打磨              后期进行
  Windows EXE 发布         待开发

## 事实说明

本仓库应作为源代码与项目文档的唯一事实来源。聊天记录可用于讨论，但若与仓库已确认文档冲突，应先提出差异并由用户确认，再更新文档。
