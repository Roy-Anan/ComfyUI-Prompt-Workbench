# R30 执行报告

## 任务

在设置页提供旧档案候选的只读预览入口，把 R8/R13 已备的档案清单与预览接口接到前端，与 R28 规则库只读清单互补：规则库展示已入库记录，本面板展示待审核旧档案候选。

## 实施步骤

1. 盘点 M3 backlog，选定前端只读对接切片；后端 `/api/profiles`、`/api/profiles/{file}` 已在 R8/R13 落地，无需后端改动。
2. `App.tsx` 新增 `ProfileCandidate` / `ProfileSummary` / `ProfilePreview` 类型；`profiles` / `openProfile` / `preview` 状态；`refresh()` 用 `Promise.all` 并行拉取档案清单。
3. `toggleProfile(file)`：收起则重置预览；展开则懒加载预览接口，失败置空预览并写入消息。
4. 面板置于规则库面板之后、服务连接之前：档案行展示文件名（回退 display_name/file）、架构、候选数、未识别字段数；解析失败档案禁用展开并显示错误。展开后嵌套候选列表，复用规则行与标签样式，展示规则键、层级、作用域、值、结构化、备注、来源/可信度/版本。
5. `styles.css` 追加 `.profile-toggle`（无边框透明底左对齐按钮）、`.profile-preview`（缩进左竖线嵌套列表，内层规则行单列）。
6. 后端回归、前端构建、真机浏览器验收；回收后端进程，核对规则表归零。

## 口径核对

- 档案匹配按完整 checkpoint 文件名精确匹配（旧 `profile_lookup.py` 口径）；前端展示字段直接取自后端解析结果，不做关键词/前缀/相似度推断。
- 纯只读：未渲染导入按钮；本轮未调用 `POST /api/profiles/import`，规则表保持 0 条。

## 结果

- 清单：13 份旧档案，候选数 11–21，未识别字段 17–26。
- 预览：Anything_V5.txt 返回 12 条候选（含 `IDENTITY::Base Architecture` 身份指针补记）。
- 进程回收：父 PID 26668、uvicorn 子 PID 6964 已回收，17890 端口释放；Ollama / ComfyUI 未动。
