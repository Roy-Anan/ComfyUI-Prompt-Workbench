# TASK-003.1-R35 证据汇总（轻量化归档）

## 范围

CLIP/VAE 接入模型身份索引与摘要挂载，沿用 Checkpoint/LoRA 同一套身份库；本批为批量终验节奏首批，真机验收在阶段收口统一进行。

## 改动

- `backend/main.py`：目录索引、摘要构建、identity 回填三段循环合并为统一 `identity_groups`，扩入 `clip`/`vae`。
- `backend/test_model_catalog.py`：新增端点用例，配置临时 clip/vae 目录后两条目身份 `known=True`、`on_disk=True`、大小一致。
- `frontend/src/App.tsx`：CLIP/VAE 清单条目由 `diskLabel` 改为统一 `identityLabel`；身份未命中回退磁盘标签。
- 文档：`docs/ROADMAP.md`、`PROJECT_STATE.md` 第 45 节；`docs/ROADMAP.md` 末尾新增「开发节奏（R35 起）」。

## 口径

- 按需哈希，不 eager；文件 size/mtime 变化使缓存哈希失效；无摘要不推断身份。
- 不拷贝权重；目录索引不递归子文件夹。
- 真机未配置 CLIP/VAE 目录，命中分支由临时目录单测覆盖。

## 测试结果

- 后端：**170 passed, 1 warning in 6.37s**（`pytest-output.txt`；StarletteDeprecationWarning 为遗留告警，与本项目无关）。
- 前端：`tsc -b && vite build` exit 0；`index-CPKxdkMV.js 165.62 kB gzip 53.30 kB`，CSS 8.09 kB（`frontend-build.txt`）。

## 边界 / backlog

- CLIP/VAE 全量/定时哈希策略与前端哈希触发入口未做。
- 真机浏览器验收留待阶段收口。
