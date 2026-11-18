# TASK-003.1-R32 M3 第二十七切片：前端星号 markdown 残留清理

## 范围

工作流工作区「当前工作流识别结果」标题行此前用 JSX 字面 `**{filename}**` 书写 markdown 加粗，浏览器不解析，界面上出现字面星号。本切片改为既有 `<strong>` 加粗标签；全前端复查无其他 markdown 残留。纯前端展示修复，后端零改动。

## 改动文件

- `frontend/src/WorkflowWorkbench.tsx`：标题行 `**{detail.manifest.filename}**` → `<strong>{detail.manifest.filename}</strong>`。

## 验收结论

- 后端 pytest：165 passed, 1 warning in 6.14s。
- 前端构建：exit 0；`index-Bgw4pSpK.js 165.10 kB`（gzip 53.22 kB），CSS 8.09 kB。
- 真机：标题行渲染为加粗文件名 + `· API · 8 个节点`，无字面星号；规则表 0 条。

## 证据清单

- `screenshots/title-bold.png`：识别结果标题行。
- `pytest-output.txt` / `frontend-build.txt` / `git-diff.md` / `git-diff-raw.txt` / `known-issues.md`。
