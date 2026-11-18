# Doubao 回执 — TASK-003.1-R28

## 任务

M3 第二十三切片：规则库只读清单界面。此前规则记录只在工作流比对面板间接可见，本切片在设置页提供分组只读清单。

## 完成内容

- `frontend/src/App.tsx`：`RuleRecord` 类型与层级/来源/可信度中文标签映射；`refresh()` 并行拉取 `/api/rules`；按 checkpoint / architecture / global 三级分组展示规则键、作用域、原始值、结构化摘要、备注及来源、可信度、版本标签；空库提示「规则库为空」。
- `frontend/src/styles.css`：规则分组标题、条目行与标签样式。
- 文档：`PROJECT_STATE.md` 第 38 节、`docs/ROADMAP.md` 回填 R28。

## 口径

- 面板数据来自 `GET /api/rules`，纯只读；前端不提供规则新增、修改、删除入口。

## 自测结果

- 后端：**164 passed, 1 warning in 6.15s**（无后端逻辑改动，回归全绿）。
- 前端：`tsc -b && vite build` exit 0；`index-8q4qtSIr.js 161.93 kB │ gzip 52.39 kB`。
- 真机浏览器（`samples/rules-payload.json`）：导入 PonyDiffusion 档案 20 条，checkpoint 15 / architecture 5 / global 0；模型档案与架构基线两组条目、来源/可信度/版本标签与后端记录一致。
- 截图 `screenshots/rules-checkpoint-group.png`、`rules-architecture-group.png`；清理后规则表 0 条。

## Git

- 功能提交：`8572e386824fa5904de157268d824be513acf4f8`（本地 dev，已推送 origin/dev）。
- 远端核对：连接器 `list_commits(dev)` 最新提交即 `8572e38`，消息「feat(workbench): M3 第二十三切片 规则库只读清单界面」，作者 Roy-Anan / 1538072315@qq.com。
- main 分支未改动。

## 边界

- 规则候选勾选/驳回、人工编辑/删除、档案审核导入前端入口与冲突人工处理界面为后续切片；清单未做筛选与搜索。
