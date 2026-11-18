# TASK-003.1-R30 M3 第二十五切片：旧档案候选只读预览界面

## 范围

设置页「旧档案候选（只读）」面板，对接既有后端只读接口：

- `GET /api/profiles`：旧档案清单（文件名、识别架构、候选数、未识别字段数、解析错误）。
- `GET /api/profiles/{file}`：单份档案候选预览（层级、作用域、原始值、结构化摘要、备注、来源、可信度、版本）。

本切片**后端零改动**；前端纯只读展示，不提供导入、勾选、驳回等写控件。

## 改动文件

- `frontend/src/App.tsx`：档案候选类型、state、refresh 并行拉取、懒加载展开函数、面板 JSX。
- `frontend/src/styles.css`：`.profile-toggle`、`.profile-preview` 及内层规则行单列样式。
- `PROJECT_STATE.md`：回填第 40 节。

## 验收结论

- 后端 pytest：165 passed, 1 warning in 6.10s。
- 前端构建：exit 0；`index-Cw2T345o.js 164.26 kB`（gzip 52.99 kB），CSS 8.09 kB。
- 真机浏览器：13 份档案列出；展开 Anything_V5 显示 12 条候选明细；面板无写控件；规则表保持 0 条。

## 证据清单

- `samples/profiles-payload.json`：清单与预览 API 原始载荷。
- `screenshots/profiles-list.png`：档案清单面板。
- `screenshots/profile-preview.png`：展开后的候选明细。
- `pytest-output.txt` / `frontend-build.txt`：测试与构建输出。
- `git-diff.md` / `git-diff-raw.txt`：本切片代码改动。
- `known-issues.md`：遗留与 backlog。
