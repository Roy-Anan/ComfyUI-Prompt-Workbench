# 测试结果 — TASK-003.1-R7

## 后端 pytest

- 命令：`.venv\Scripts\python.exe -m pytest -q`（`backend/`）
- 结果：**77 passed, 1 warning in 4.26s**
- 警告：既有 `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated`，非失败。
- 原始输出：`pytest-output.txt`

### 本轮新增/覆盖用例

`test_model_identity.py`（7 例）：

| 用例 | 覆盖点 |
| --- | --- |
| `test_index_directory_records_weight_metadata` | 目录索引记录路径/大小/mtime，sha256 初始为空 |
| `test_index_ignores_non_weight_files` | 非权重后缀不入库 |
| `test_changed_file_invalidates_cached_digest` | 大小/mtime 变化后缓存哈希失效置空 |
| `test_ensure_hash_computes_and_caches` | 按需计算并缓存摘要，复调复用 |
| `test_identity_summary_unknown_when_not_recorded` | 无记录返回 `{known:false}` |
| `test_identity_summary_reports_cached_state` | 有记录回挂 on_disk/大小/未哈希 |
| `test_unknown_category_rejected` | 未知类别拒绝索引 |

`test_model_catalog.py` 追加：

| 用例 | 覆盖点 |
| --- | --- |
| `test_catalog_endpoint_attaches_identity_for_configured_dir` | 配置真实目录后条目回挂 identity：known/on_disk/size_bytes/hashed=false/sha256=null |

## 前端构建

- 命令：`npm run build`（`frontend/`，即 `tsc -b && vite build`）
- 结果：exit 0，33 模块；产物 `dist/`（JS 156.95 kB / gzip 50.82 kB，CSS 5.44 kB）。
- 原始输出：`frontend-build.txt`

## 真机核对

- 见 `samples/identity-summary.json` 与 `screenshots/`。
