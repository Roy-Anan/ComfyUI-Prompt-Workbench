# Doubao 回执 — TASK-003.1-R30

## 任务

M3 第二十五切片：旧档案候选只读预览界面。R8/R13 已落地档案清单与候选预览只读接口，R28 前端只做了已入库规则清单；本切片把待审核旧档案候选接到设置页，纯只读展示，不开放导入/勾选/驳回写控件。

## 完成内容

- `frontend/src/App.tsx`：新增 `ProfileCandidate` / `ProfileSummary` / `ProfilePreview` 类型；`profiles` / `openProfile` / `preview` 状态；`refresh()` 并行拉取 `GET /api/profiles`；`toggleProfile(file)` 懒加载 `GET /api/profiles/{file}`；规则库面板之后新增「旧档案候选（只读）」面板。
- `frontend/src/styles.css`：新增 `.profile-toggle`、`.profile-preview` 及内层规则行单列样式。
- 文档：`PROJECT_STATE.md` 第 40 节回填 R30。
- 后端零改动。

## 口径

- 档案身份以完整 checkpoint 文件名精确匹配；前端展示字段直接取自后端解析结果，不做关键词/前缀/相似度推断。
- 纯只读：未渲染导入按钮，未调用 `POST /api/profiles/import`；本轮规则表保持 0 条。

## 自测结果

- 后端：**165 passed, 1 warning in 6.10s**。
- 前端：`tsc -b && vite build` exit 0；`index-Cw2T345o.js 164.26 kB │ gzip 52.99 kB`，CSS 8.09 kB。
- 真机浏览器：13 份旧档案列出（候选 11–21，未识别 17–26）；展开 Anything_V5.txt 显示 12 条候选，层级/作用域/值/备注/来源/可信度/版本标签齐全；面板无写控件。截图 `screenshots/profiles-list.png`、`screenshots/profile-preview.png`；载荷 `samples/profiles-payload.json`。
- 清理后规则表 0 条；后端进程已回收，17890 端口释放。

## Git

- 功能提交：`4c08f20547dfe04dc40dd46e22b3c7fcac85c2da`（本地 dev，已推送 origin/dev）。
- 远端核对：连接器 `list_commits(dev)` 最新提交即 `4c08f20`，消息「feat(workbench): M3 第二十五切片 旧档案候选只读预览界面」，作者 Roy-Anan / 1538072315@qq.com。
- main 分支未改动。

## 边界

- 候选勾选/驳回/差异预览与前端规则、档案管理写界面留后续切片。
