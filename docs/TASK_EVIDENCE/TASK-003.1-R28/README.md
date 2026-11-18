# TASK-003.1-R28 证据目录

M3 第二十三切片：规则库只读清单界面。

## 交付物

- `frontend/src/App.tsx`：`RuleRecord` 类型、规则状态与拉取；按三级分组的只读规则面板，含规则键、作用域、原始值、结构化摘要、来源、可信度、版本、备注。
- `frontend/src/styles.css`：规则分组与条目行样式。

## 口径

- 面板数据来自 `GET /api/rules`，纯只读；前端不开放规则新增、修改、删除。
- 层级中文标签：checkpoint 模型档案 / architecture 架构基线 / global 全局规则。

## 验收记录

| 项 | 结果 |
| --- | --- |
| 后端 pytest | 164 passed, 1 warning（见 `pytest-output.txt`） |
| 前端构建 | tsc -b && vite build exit 0（见 `frontend-build.txt`） |
| 真机浏览器 | `screenshots/rules-checkpoint-group.png`、`rules-architecture-group.png`；载荷 `samples/rules-payload.json` |
