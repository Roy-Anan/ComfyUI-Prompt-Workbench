# R34 执行报告

## 任务

catalog 的 CLIP/VAE 名称此前已从 `/object_info` 提取，但本机存在性核对恒为 `None`。本切片把 CLIP/VAE 接入与 Checkpoint/LoRA 一致的只读目录核对链路，不进身份哈希库。

## 实施步骤

1. `datadir`：`OPTIONAL_EXTERNAL_KEYS` 增加 `clip`、`vae`；默认 storage 补两个空串键；迁移合并白名单随既有常量自动覆盖。
2. `model_catalog.fetch_catalog`：签名增加 `clip_dir`、`vae_dir`；`clips`、`vaes` 由恒 `None` 改为走 `_annotate`。
3. `_annotate` 修正判定：目录已配置且存在时按索引判 `True/False`；目录未配置或不存在时返回 `None`（未知）。空的已配置目录不再被误判为未知。
4. `main.py` catalog 调用从 storage 补传 `clip_dir`、`vae_dir`。
5. 前端：`storageLabels` 补 CLIP/VAE；外部目录集合抽常量 `EXTERNAL_STORAGE_KEYS` 与 `isExternalStorageKey`，复用在「不自动创建」与「外部可留空」两处判断；清单网格补 CLIP 列（复用 VAE 列 `diskLabel` 范式）。
6. 补后端单测：CLIP 命中/未找到、VAE 空目录未找到、未配置目录未知；settings 空串白名单覆盖 clip/vae。
7. 后端回归、前端构建；真机浏览器核对四列与外部目录标签；清理规则表，回收后端进程。

## 真机结果

| 分组 | 数量 | on_disk（目录未配置） |
| --- | --- | --- |
| Checkpoint | 13 | 全部 `None` |
| LoRA | 3 | 全部 `None` |
| CLIP | 0 | ComfyUI 未列出 CLIP |
| VAE | 3（animevae.pt / pixel_space / vae-ft-mse-840000-ema-pruned.safetensors） | 全部 `None` |

存储区外部目录标签：Checkpoint / LoRA / CLIP / VAE 四项，均可留空。目录命中与未找到分支由临时目录单测覆盖，未改动真机 userdata 目录配置。

## 进程回收

- 后台启动 PID 5784、uvicorn 子 PID 19680 已核对命令行与可执行路径后回收，17890 释放；规则表 0 条；未写入任何真机模型目录。
