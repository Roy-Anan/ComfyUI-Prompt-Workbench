# R30 Git Diff 摘要

基线：`c9b1d83`（R29 回执提交）。本切片未触碰 `main`。

## 改动统计

```
 frontend/src/App.tsx    | 147 +++++++++++++++++++++++++++++++++++++++++++++++-
 frontend/src/styles.css |  30 ++++++++++
 2 files changed, 176 insertions(+), 1 deletion(-)
```

## 改动要点

### `frontend/src/App.tsx`

- 新增类型 `ProfileCandidate`、`ProfileSummary`、`ProfilePreview`。
- 新增状态 `profiles`、`openProfile`、`preview`。
- `refresh()` 的 `Promise.all` 增加 `GET /api/profiles`。
- 新增 `toggleProfile(file)`：收起重置预览；展开懒加载 `GET /api/profiles/{file}`，失败置空并写消息。
- 规则库面板之后新增「旧档案候选（只读）」面板：清单行展示文件名/架构/候选数/未识别字段数；展开后嵌套候选规则行，复用层级/来源/可信度/版本标签。

### `frontend/src/styles.css`

- 新增 `.profile-toggle`（透明底、左对齐、禁用态）、`.profile-preview`（缩进左竖线嵌套列表），内层规则行单列布局。

### `PROJECT_STATE.md`

- 回填第 40 节 R30 状态、验收结果与 backlog。

完整补丁见 `git-diff-raw.txt`。
