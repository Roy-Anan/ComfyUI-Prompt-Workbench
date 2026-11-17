# 数据目录报告 — TASK-002.3.1

## 1. 目录口径

| 项 | 旧根（保留，不再使用） | 新根（默认） |
| --- | --- | --- |
| 路径 | `%LOCALAPPDATA%\ComfyUI-Prompt-Workbench` | 仓库内 `userdata/`（`D:\AI\ComfyUI-Prompt-Workbench-Git\userdata`） |
| 环境变量覆盖 | — | `WORKBENCH_DATA_ROOT` 可覆盖默认根 |
| Git 跟踪 | — | 被 `.gitignore` 的 `/userdata/` 规则忽略，不入库 |

## 2. 迁移前旧根内容（保留）

- `settings.json`（1139 B，旧根根级配置，含旧 AppData 管理路径）。
- `database\workbench.sqlite3`（16384 B）。
- 其余历史子目录为空；无 WAL/SHM 副文件。
- 旧库实测：`integrity_check = ok`；表 `schema_version`、`app_metadata`；`schema_version = 1`；元数据 `application = ComfyUI-Prompt-Workbench`。

## 3. 迁移后新根内容

```text
userdata/
├── backups/
│   └── legacy-migration-20261117-145437/
│       └── database/
│           └── workbench.sqlite3   (16384 B，旧库备份)
├── database/
│   └── workbench.sqlite3           (16384 B，迁入库)
├── settings/
│   └── settings.json              (1007 B，按新根重建)
├── knowledge/ prompts/ workflows/ drafts/ history/
├── cache/ logs/ exports/          (空管理目录)
```

- 迁入库实测：`integrity_check = ok`，`schema_version = 1`，元数据正常。
- 新根设置文件中管理路径全部指向项目内 `userdata/`；外部 `checkpoint` / `lora` 路径为空（保留用户既有外部目录登记口径，本次未填写）。
- 旧根根级 `settings.json` 未复制到新根（管理路径按新根重建）；旧目录与旧文件原样保留。

## 4. 忽略与隔离核对

- `userdata/settings/settings.json` → `.gitignore:28 /userdata/` 命中。
- `userdata/database/workbench.sqlite3` → `.gitignore:28 /userdata/` 命中。
- 提交前扫描：待提交文件中无数据库文件、模型权重、原始图片、API 密钥或账号信息。

## 5. 边界说明

- 模型权重、原图、原始工作流仍在 ComfyUI 原有外部目录管理，工作台只记录路径与索引，不复制进 `userdata/`。
- 本任务不删除旧目录、不重建数据库规避迁移；迁移失败时旧数据保留并在报告中标注。
