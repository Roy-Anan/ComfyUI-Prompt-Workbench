# 执行报告 — TASK-003.1-R7

## 基线

- 开发分支 `dev`，基线提交 `d8f8778`（M3 第一切片 R6），本地与 origin/dev 同步；main `3084866` 未改、未合并。
- 版本 `0.1.0-dev.5`（本轮未 bump）。

## 改动内容

### 后端

- 新增 `backend/model_identity.py`：
  - SQLite `model_identity` 表：`category` + `relative_name` 唯一，字段含 `absolute_path`、`size_bytes`、`mtime_ns`、`sha256`、`hashed_at`、`last_seen_at`。
  - `index_directory`：只扫直下层权重后缀（`.safetensors/.ckpt/.pt/.pth/.bin/.gguf`），刷新大小/mtime；元数据变化时置空缓存哈希。
  - `sha256_file`：分块流式计算 SHA256，不全量读入内存。
  - `ensure_hash`：对已记录且在盘的文件按需计算并缓存摘要；无记录返回 None。
  - `identity_summary`：无记录返回 `{"known": False}`；有记录回挂 known/on_disk/size_bytes/sha256/hashed。
- `backend/main.py`：`initialize_database` 调用 `model_identity.ensure_schema`；`GET /api/models/catalog` 在已配置 checkpoint/lora 目录时索引身份库，并给清单条目回挂 `identity` 摘要。
- 测试：新增 `backend/test_model_identity.py`（7 例）；`backend/test_model_catalog.py` 追加 1 例接口身份回挂测试。

### 前端

- `frontend/src/App.tsx`：新增 `IdentitySummary` 类型、`formatSize`（GB/MB/B）、`identityLabel`；Checkpoint 与 LoRA 列表右侧标签改为身份摘要（大小 · 已校验/未哈希），无记录时回退存在性标签。VAE 列沿用存在性标签（身份库未索引 VAE/CLIP）。

## 真机执行

1. 健康检查 `/api/health` 200，实例标识正常；ComfyUI 8188、Ollama 11434 在线。
2. 通过会话接口将 `storage.checkpoint`、`storage.lora` 指向真机目录，调用 `/api/models/catalog`：
   - online=true；Checkpoint 13、LoRA 3。
   - 样例 checkpoint `CyberRealisticPony_V18.0_F16.safetensors`：known=true、on_disk=true、size_bytes=6,938,041,288、hashed=false、sha256=null。
   - 样例 LoRA `ip-adapter-faceid-plusv2_sd15_lora.safetensors`：size_bytes=51,059,544、hashed=false。
3. 对最小 LoRA `suyuexi.safetensors`（37,866,968 字节）调用 `ensure_hash`：摘要前缀 `fedeb940e772`，`hashed_at` 落时间戳；复调复用缓存。
4. 核对后将 `storage.checkpoint`、`storage.lora` 恢复为空串。
5. 浏览器打开 `http://127.0.0.1:17890/`：服务在线，清单大小与未哈希/已校验标签渲染正确，截图归档。

## 结果

- 后端 pytest **77 passed**（1 条既有 StarletteDeprecationWarning，非失败）。
- 前端 `tsc -b && vite build` exit 0，33 模块。
