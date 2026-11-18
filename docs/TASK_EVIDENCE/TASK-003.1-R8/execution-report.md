# 执行报告 — TASK-003.1-R8

## 基线

- 开发分支 `dev`，基线提交 `4e71bbc`（R7 回执回填）；main `3084866` 未改、未合并。
- 版本 `0.1.0-dev.5`（本轮未 bump）。

## 改动内容

### 后端 `backend/model_identity.py`

- 新增 `_copies_with_digest`：同类别内按 `sha256` 查全部副本记录。
- 新增 `identity_group`：按文件名解析到摘要身份组；有摘要时返回 `identity_key`（`category:digest`）、`digest`、`copies`（相对名/绝对路径/在盘/大小）；无摘要时 `identity_key=None`、`copies=[]`，不做哈希推断；无记录返回 `{known:False}`。
- `identity_summary` 回挂 `identity_key`、`copy_count`、`copies`。

### 测试 `backend/test_model_identity.py`

- `test_identical_copies_share_one_identity`：两份相同内容副本归并到同一身份键，`copy_count=2`。
- `test_different_content_not_merged`：不同摘要不合并，各 `copies=1`。
- `test_unhashed_group_has_no_identity_key`：未哈希文件身份键为空、副本列表为空。

### 前端 `frontend/src/App.tsx`

- 补充 `IdentityCopy` 类型与 `IdentitySummary` 的 `identity_key`/`copy_count`/`copies` 字段。

## 真机执行

1. 健康检查 200；ComfyUI 8188、Ollama 11434 在线。
2. 配置真机 checkpoint/lora 目录，`/api/models/catalog` online=true，13 ckpt / 3 lora。
3. 对最小 LoRA `suyuexi.safetensors`（37,866,968 字节）`ensure_hash`：身份键 `lora:fedeb940e7725e869fc51b7fe2c1d776ee9c460b6598810ec82b8f0f7fb69b1d`，`copy_count=1`（本机无重复副本）；清单摘要回挂 `identity_key`/`copy_count`/`copies`。
4. 核对后目录设置恢复空串。
5. 浏览器打开 `http://127.0.0.1:17890/`：清单已校验/未哈希标签正常，截图归档。

## 结果

- 后端 pytest **80 passed**（1 条既有 StarletteDeprecationWarning，非失败）。
- 前端 `tsc -b && vite build` exit 0，33 模块。
