# R33 Git Diff 摘要

基线：`9fa84d1`（R32 回执提交）。本切片未触碰 `main`。

## 改动统计

```
 backend/value_normalize.py          | 30 ++++++++++++++++++++-
 backend/test_value_normalize.py    | 40 +++++++++++++++++++++++++++
 frontend/src/format.ts             |  8 +++++++
 3 files changed
```

## 改动要点

### `backend/value_normalize.py`

- 新增 `_split_sets`：按 `；`/`;` 拆分多套建议，保留顺序、去空。
- `normalize`：多套逐套解析，全部成功才产出 `{"kind":"sets","items":[...]}`；任一失败整体 `structured=None`。
- `normalize_list`：新增 `_MISSING_MARKERS` 与 `_is_missing_token`；缺失标记 token 视为不可用，返回 None。

### `backend/test_value_normalize.py`

- 双套全成功出 sets（Steps/CFG/Sampler/Resolution）；双套任一失败整体 None；list 缺失标记归 None。

### `frontend/src/format.ts`

- `formatStructured` 新增 `sets` 分支：各套递归摘要，以 `；` 连接。

### 比对层

- `rule_compare.py` 零改动；`sets` 落入既有 `structured_kind_unhandled` 分支归 unknown。

完整补丁见 `git-diff-raw.txt`。
