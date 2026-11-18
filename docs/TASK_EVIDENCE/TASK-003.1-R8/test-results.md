# 测试结果 — TASK-003.1-R8

## 后端 pytest

- 命令：`.venv\Scripts\python.exe -m pytest -q`（`backend/`）
- 结果：**80 passed, 1 warning in 4.44s**
- 警告：既有 `StarletteDeprecationWarning`，非失败。
- 原始输出：`pytest-output.txt`

### 本轮新增用例

| 用例 | 覆盖点 |
| --- | --- |
| `test_identical_copies_share_one_identity` | 相同内容两副本同身份键、`copy_count=2`、副本列表齐全 |
| `test_different_content_not_merged` | 不同摘要不合并，各自 `copies=1` |
| `test_unhashed_group_has_no_identity_key` | 未哈希文件 `identity_key=None`、`copies=[]` |

既有 R7 用例（7 例身份库 + 1 例接口回挂）继续通过。

## 前端构建

- 命令：`npm run build`（`frontend/`，即 `tsc -b && vite build`）
- 结果：exit 0，33 模块；产物 `dist/`（JS 156.95 kB / gzip 50.82 kB，CSS 5.44 kB）。
- 原始输出：`frontend-build.txt`

## 真机核对

- 见 `samples/merge-summary.json` 与 `screenshots/`。
