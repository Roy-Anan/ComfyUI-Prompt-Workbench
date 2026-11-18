# TASK-003.1-R34 M3 第二十九切片：VAE/CLIP 目录只读核对链路

## 范围

此前 catalog 已从 `/object_info` 提取 CLIP、VAE 名称，但两者 `on_disk` 恒为 `None`（未接本地目录核对）。本切片把 CLIP/VAE 纳入与 Checkpoint/LoRA 同一套只读目录存在性核对：配置了目录才逐项核对命中与否；未配置目录时 `on_disk=None`（未知，不报未找到）。不进身份哈希库、不拷贝权重、不算摘要。

## 改动文件

- `backend/datadir.py`：`OPTIONAL_EXTERNAL_KEYS` 扩为 `checkpoint/lora/clip/vae`；默认 storage 补 `clip`、`vae` 空串。
- `backend/model_catalog.py`：`fetch_catalog` 新增 `clip_dir`、`vae_dir`；`clips`/`vaes` 改走 `_annotate`；`_annotate` 按「目录已配置且存在」区分命中/未找到与未知。
- `backend/main.py`：catalog 调用补传 `clip_dir`、`vae_dir`。
- `backend/test_model_catalog.py`：CLIP/VAE 目录命中、未找到、未配置未知用例；兼容 fake catalog 签名。
- `backend/test_main.py`：外部目录空串白名单用例覆盖 clip/vae。
- `frontend/src/App.tsx`：存储标签补 CLIP/VAE；外部目录口径抽为 `EXTERNAL_STORAGE_KEYS`/`isExternalStorageKey`；清单网格补 CLIP 列。

## 口径

- 只读存在性核对，不复制、不改写模型目录，不计算哈希/摘要。
- 目录未配置（或路径不存在）→ `on_disk=None`，保守视为未知；目录已配置但为空 → 列出项判 `False`（本机未找到），不混同为未知。
- CLIP/VAE 不接入身份哈希索引；其身份归并、大小/校验仍属后续链路。

## 验收结论

- 后端 pytest：**169 passed, 1 warning in 6.34s**。
- 前端构建：exit 0；`index-DJeMbr87.js 165.64 kB`（gzip 53.30 kB），CSS 8.09 kB。
- 真机：目录均未配置，Checkpoint 13、LoRA 3、CLIP 0（ComfyUI 未列出）、VAE 3，`on_disk` 全部 `None`；存储区四个外部目录标签齐全、均可留空。
- 清理后规则表 0 条；后端进程已回收，17890 释放。

## 证据清单

- `samples/catalog-payload.json`：真机 catalog 载荷（clips/vaes 未配置目录口径）。
- `screenshots/catalog-four-columns.png`：清单 Checkpoint/LoRA/CLIP/VAE 四列与外部目录标签。
- `pytest-output.txt` / `frontend-build.txt` / `git-diff.md` / `git-diff-raw.txt` / `known-issues.md`。
