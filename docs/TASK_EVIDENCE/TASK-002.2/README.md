# TASK-002.2 证据归档 — Windows 用户运行环境盘点与桌面应用交付准备

- 任务编号：TASK-002.2
- 分支：`dev`（未合并 `main`）
- 采集时间：2026-11-17 21:59（UTC+8）
- 采集方式：只读检测，未安装任何开发软件，未修改系统 PATH / 注册表 / 环境变量 / 防火墙 / 杀毒设置
- 分工口径：ChatGPT 负责代码编写、技术设计与代码审查；豆包负责本地文件操作、运行验证、证据收集与 GitHub 提交；用户负责使用与验收

## 本目录文件

| 文件 | 内容 |
| --- | --- |
| `environment-report.md` | Windows 版本/架构、管理员权限、磁盘空间、WebView2、Edge、VC++ 运行时、Python 与项目 `.venv` 现状 |
| `runtime-dependency-report.md` | 最终用户运行依赖 vs 开发依赖；运行时所需组件、可随包提供组件、系统已有组件、缺失才需安装组件 |
| `installer-design-report.md` | 目标交付形态、PyInstaller sidecar、Tauri 打包、数据目录与卸载保护、体积估算与不确定性 |
| `current-code-review.md` | 基于当前代码的现状核对、发现的问题与影响（不做大规模重构） |
| `disk-space-report.md` | 磁盘容量与仓库盘剩余空间记录 |
| `known-issues.md` | 阻断项、待确认项与后续责任分工 |
| `raw-outputs/` | 原始命令输出与采集快照（不含密钥、模型权重、虚拟环境、构建产物） |

## 边界声明

- 本任务**不宣布 M0 桌面闭环通过**，也**不宣布正式 EXE 已经完成**。
- 当前机器未具备桌面开发构建环境（无 Rust 工具链、无 MSVC），本任务不安装该环境。
- 报告中的体积为估算值，依据见 `installer-design-report.md`，不代表最终安装包实测大小。
- 所有版本号、路径、退出码均来自本机真实采集；未伪造截图。
