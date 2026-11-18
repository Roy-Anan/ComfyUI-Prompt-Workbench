# Doubao 回执 — TASK-003.1-R34

## 任务

M3 第二十九切片：VAE/CLIP 目录只读核对链路。catalog 的 CLIP/VAE 名称此前已从 `/object_info` 提取，但本机存在性核对恒为 `None`；本切片把两者接入与 Checkpoint/LoRA 一致的只读目录核对，不进身份哈希库、不拷贝权重。

## 完成内容

- `backend/datadir.py`：`OPTIONAL_EXTERNAL_KEYS` 扩为 `checkpoint/lora/clip/vae`；默认 storage 补 `clip`、`vae` 空串。
- `backend/model_catalog.py`：`fetch_catalog` 新增 `clip_dir`/`vae_dir`；`clips`/`vaes` 走 `_annotate`；`_annotate` 区分已配置目录命中/未找到与未配置未知，空的已配置目录不再误判未知。
- `backend/main.py`：catalog 调用补传 `clip_dir`/`vae_dir`。
- `backend/test_model_catalog.py`：CLIP 命中/未找到、VAE 空目录未找到、未配置未知；fake 签名兼容。
- `backend/test_main.py`：外部目录空串白名单覆盖 clip/vae。
- `frontend/src/App.tsx`：CLIP/VAE 存储标签；外部目录口径抽 `EXTERNAL_STORAGE_KEYS`/`isExternalStorageKey`；清单网格补 CLIP 列。
- 文档：`PROJECT_STATE.md` 第 44 节、`docs/ROADMAP.md` 回填 R34。

## 口径

- 只读存在性核对：不复制、不改写模型目录，不计算哈希/摘要。
- 目录未配置或路径不存在 → `on_disk=None`（未知）；目录已配置 → 逐项 `True/False`。
- CLIP/VAE 不接入身份哈希索引；身份归并、大小/校验标注属后续链路。

## 自测结果

- 后端：**169 passed, 1 warning in 6.34s**。
- 前端：`tsc -b && vite build` exit 0；`index-DJeMbr87.js 165.64 kB │ gzip 53.30 kB`，CSS 8.09 kB。
- 真机：目录未配置，Checkpoint 13、LoRA 3、CLIP 0（未列出）、VAE 3，`on_disk` 全部 `None`；存储区四个外部目录标签齐全、可留空。截图 `screenshots/catalog-four-columns.png`；载荷 `samples/catalog-payload.json`。
- 规则表 0 条；后端进程已回收，17890 端口释放。

## Git

- 功能提交：`e8ca236b415a4793e31d2e17b5498627a022f9fa`（本地 dev，已推送 origin/dev）。
- 远端核对：连接器 `list_commits(dev)` 最新提交即 `e8ca236b`，消息「feat(workbench): M3 第二十九切片 CLIP/VAE 目录只读核对链路」，作者 Roy-Anan / 1538072315@qq.com。
- main 分支未改动。

## 边界

- CLIP/VAE 未进身份哈希库；目录索引不递归子文件夹；真机未配置 CLIP/VAE 目录，命中分支由临时目录单测覆盖。
