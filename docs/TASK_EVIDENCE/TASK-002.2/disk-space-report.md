# 磁盘空间报告

- 采集时间：2026-11-17 21:59（UTC+8）
- 原始输出：`raw-outputs/disk-space.txt`
- 采集方式：只读查询 `Win32_LogicalDisk` 与 `Get-PSDrive`，未写入或清理任何磁盘内容

## 1. 固定磁盘容量

| 盘符 | 可用空间 | 总容量 | 已用（D 盘） | 说明 |
| --- | --- | --- | --- | --- |
| C: | 45.95 GB（47055.1 MB） | 152.79 GB | — | 系统盘；默认用户数据根在 `%LOCALAPPDATA%`（C 盘） |
| D: | 49.11 GB（50288.5 MB） | 323.20 GB | 274.1 GB | 项目仓库所在盘 |

## 2. 项目仓库位置

- 路径：`D:\AI\ComfyUI-Prompt-Workbench-Git`
- 所在磁盘：D 盘，剩余约 49.11 GB，足以容纳源码、`.venv`（约 28.3 MB）、`node_modules`（约 79.4 MB）与前端产物。

## 3. 运行期数据增长位置

- 默认数据根：`C:\Users\15380\AppData\Local\ComfyUI-Prompt-Workbench`（当前不存在，首次启动后创建）。
- 增长内容：SQLite 数据库、knowledge / prompts / workflows / drafts / history / exports、备份与日志。
- 模型权重（Checkpoint / LoRA）由用户登记到自有目录，**不计入工作台数据目录增长**；安装包不携带模型。

## 4. 规划提示（供打包设计参考）

- C 盘剩余约 46 GB，对工作台自身元数据、草稿、历史与导出而言充足；但用户若把导出图片、快照存到数据根，长期占用需在产品层面提供查看与清理入口。
- 仓库与开发依赖放在 D 盘；正式安装包默认装到用户可写目录，用户数据走 `%LOCALAPPDATA%`，避免把数据写进安装目录。
- 磁盘数值为采集时点快照，不代表长期可用空间。
