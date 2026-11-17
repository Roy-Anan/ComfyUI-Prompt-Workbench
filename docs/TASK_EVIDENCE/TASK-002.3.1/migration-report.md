# 迁移报告 — TASK-002.3.1

## 1. 迁移动作

- 触发方式：新根为空、旧根存在且含数据时，后端首次加载设置（`load_settings()`）自动执行。
- 迁移报告（本次实测）：

```json
{
  "legacy_root_exists": true,
  "legacy_has_data": true,
  "target_has_data": false,
  "action": "migrated",
  "details": "Migrated 1 file(s) from legacy root; old directory kept.",
  "backup": "backups\\legacy-migration-20261117-145437",
  "database_integrity": true
}
```

## 2. 备份

- 备份目录：`userdata/backups/legacy-migration-20261117-145437/`。
- 备份内容：旧库 `database/workbench.sqlite3`（16384 B）。
- 备份只收录非空文件，排除历次迁移备份目录与旧根根级 `settings.json`；空目录树不复制。

## 3. 复制与校验

- 迁入文件：`database/workbench.sqlite3`（16384 B）。
- SQLite 校验：迁入库 `PRAGMA integrity_check = ok`；表结构与版本保留（`schema_version = 1`）。
- 设置文件：按新根重建于 `settings/settings.json`；外部模型路径（checkpoint/lora）留空保留口径。

## 4. 旧数据处置

- 旧根 `%LOCALAPPDATA%\ComfyUI-Prompt-Workbench` 原样保留：
  - `database\workbench.sqlite3`（16384 B，完整性 ok）。
  - `settings.json`（1139 B）。
- 未删除、未覆盖旧目录；未重建数据库规避迁移。

## 5. 冲突与失败口径

- 新根已有数据：记录 `skipped-conflict`，不覆盖目标文件。
- SQLite 完整性校验失败：保留旧数据，报告标注 `failed-integrity`，不静默继续。
- 非 SQLite 文件（设置、知识、草稿等）不做 SQLite 完整性校验。
