# 已知问题与待办 — TASK-002.2

- 记录时间：2026-11-17 21:59（UTC+8）
- 状态口径：未完成项不标为已完成；阻断项交 ChatGPT 设计修复，豆包后续在用户电脑执行与实测。

## 1. 阻断项（影响桌面程序构建 / 打包）

| 编号 | 问题 | 证据 / 复现 | 影响 | 责任分工 |
| --- | --- | --- | --- | --- |
| B1 | 本机无 Rust 工具链（rustc/cargo/rustup 均缺失，`~/.cargo`、`~/.rustup` 不存在） | `raw-outputs/env-windows-runtime.txt` 中 Rust 段 | 无法编译 Tauri 主程序；本任务按要求不安装 | 打包环境由后续任务准备；代码与打包方案由 ChatGPT 设计 |
| B2 | 本机无 MSVC / Visual Studio（cl.exe、link.exe、vswhere 缺失） | 同上 MSVC/VS 段 | 即使装 Rust，Windows 链接 Tauri 也需要该工具链 | 同上 |
| B3 | sidecar 启动代码仍按开发方式查找 Python（`.venv` / 系统 `python`） | `current-code-review.md` 2.1 | 干净机器上打包产物无法拉起后端 | ChatGPT 设计生产 sidecar 启动路径，豆包后续实测 |
| B4 | Tauri bundle / NSIS / externalBin 打包配置未启用（`bundle.active=false`） | `current-code-review.md` 2.2 | 暂无可分发安装包 | ChatGPT 补齐打包配置，豆包后续构建验收 |

## 2. 待对齐 / 优化项（非当前功能阻断）

| 编号 | 问题 | 说明 |
| --- | --- | --- |
| O1 | 版本号两处不一致：`tauri.conf.json` 0.1.0 vs 后端 `0.1.0-dev.2` | 发布前统一版本规则 |
| O2 | 后端 requirements 混入 pytest 测试依赖 | 打包前拆分运行/测试依赖，减小 sidecar 体积 |
| O3 | CSP 当前为 null | 后续安全阶段按 Tauri 2 指南收紧 |
| O4 | Python 3.12 未安装；后端当前在 3.13.18 测试通过 | 3.12 兼容性未验证；正式 sidecar 以 PyInstaller 打包后不依赖用户 Python |

## 3. 未验证项（受环境限制，未在本机跑通）

- Tauri 桌面窗口启动、sidecar 自动拉起、端口/令牌壳内握手、退出子进程清理：依赖 Rust/MSVC，未编译运行。
- PyInstaller 后端打包产物及其在干净 Win11 x64 上的 DLL 依赖：尚未生成。
- WebView2 在 Tauri 壳内的实际渲染：注册表口径已识别，壳内表现待真机验证。
- 正式安装包的安装、升级、卸载与用户数据保护流程：尚未实现，未验收。

## 4. 本次任务明确未做的事

- 未安装 Rust、MSVC、Node.js、Python 3.12 或任何开发工具。
- 未修改系统 PATH、注册表、环境变量、防火墙、杀毒设置。
- 未启动/关闭/重启 ComfyUI 或 Ollama；未改动秋叶整合包及其 Python。
- 未删除现有虚拟环境、缓存、模型或用户数据。
- 未合并 `main`；未在 `main` 提交。

## 5. 后续交接

- ChatGPT：编写正式安装包代码、PyInstaller sidecar 配置、Tauri 打包配置、Windows 安装/升级逻辑、安装包构建与验收任务。
- 豆包：后续在用户电脑执行代码、实测安装包、提交证据。
- 用户：使用与最终验收。
