# R34 Git Diff 摘要

基线：`a40c2b7`（R33 回执提交）。本切片未触碰 `main`。

## 改动统计

```
 backend/datadir.py            |  4 ++-
 backend/main.py               |  2 ++
 backend/model_catalog.py      | 26 +++++++++++++-------
 backend/test_main.py          |  4 +++
 backend/test_model_catalog.py | 57 +++++++++++++++++++++++++++++++++++++++++--
 frontend/src/App.tsx          | 31 ++++++++++++++++++++---
 6 files changed, 109 insertions(+), 15 deletions(-)
```

## 改动要点

### `backend/datadir.py`

- `OPTIONAL_EXTERNAL_KEYS` 扩为 `checkpoint/lora/clip/vae`；默认 storage 补 `clip`、`vae` 空串。

### `backend/model_catalog.py`

- `fetch_catalog` 新增 `clip_dir`、`vae_dir`；`clips`、`vaes` 改走 `_annotate`。
- `_annotate` 按「目录已配置且存在」判定：已配置按索引出 `True/False`；未配置或路径不存在返回 `None`（未知）；空的已配置目录不再回退未知。

### `backend/main.py`

- catalog 调用从 storage 补传 `clip_dir`、`vae_dir`；白名单由 `OPTIONAL_EXTERNAL_KEYS` 自动覆盖新键。

### 测试

- `test_model_catalog.py`：CLIP 命中/未找到、VAE 空目录未找到、未配置未知；fake catalog 签名兼容新参数。
- `test_main.py`：外部目录空串白名单用例补 clip/vae 断言。

### `frontend/src/App.tsx`

- `storageLabels` 补 CLIP/VAE；抽 `EXTERNAL_STORAGE_KEYS`/`isExternalStorageKey` 复用到「不自动创建」与「外部可留空」两处判断；清单网格补 CLIP 列。

完整补丁见 `git-diff-raw.txt`。
