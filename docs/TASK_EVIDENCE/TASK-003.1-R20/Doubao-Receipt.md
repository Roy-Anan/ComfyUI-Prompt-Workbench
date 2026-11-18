# Doubao 回执 — TASK-003.1-R20

## 任务

M3 第十五切片：架构标签归一化与同家族规则归并。同义底座标签归到规范家族，同家族模型互相继承架构规则；混合/派生标签保守隔离，未识别标签不猜家族。

## 完成内容

- `backend/architecture_normalize.py`（新增）：`normalize(label)` / `same_family(a, b)`；规范家族 SD1.5/SDXL/Pony，未识别留 other；派生/多家族标 mixed。
- `backend/rule_store.py`：上下文按规范家族归并架构规则；身份指针优先读本模型；未登记模型家族留空；返回 `architecture_family`/`architecture_label`。
- `backend/profile_parser.py`：导入时补 checkpoint 桶 `IDENTITY::Base Architecture` 身份指针。
- `backend/rule_prompt.py`：提示载荷透传家族与原始标签。
- `backend/workflow_api.py`：未登记占位补家族/标签字段。
- 测试：`test_architecture_normalize.py`（8 例）、`test_rule_store.py`（同家族归并 + 混合隔离）、`test_profile_source.py`（身份指针断言）、`test_workflow_rules.py`（未登记不带家族）。
- 文档：`PROJECT_STATE.md` 第 30 节、`docs/ROADMAP.md` 回填 R20。

## 自测结果

- 后端：**147 passed, 1 warning in 5.79s**。
- 前端：`tsc -b && vite build` exit 0；`index-IXKUmsZF.js 156.95 kB`、CSS 5.44 kB。
- 真机冒烟（`samples/smoke-normalize.json`）：
  - 导入 huslyorealismxl（SDXL，19）、intorealismUltra（SDXL 1.0，17）、ponyDiffusionV6XL（Pony / SDXL 系，20），0 拒绝。
  - intorealismUltra 上下文：family=SDXL，label=SDXL 1.0；架构 scope = `SDXL`、`SDXL 1.0`；混合标签未纳入；提示 17 字段。
  - 清理后规则表 0 条。

## 过程修正

- 未登记 checkpoint 被跨桶挂上无关 Pony 标签：根因是 R16 家族线索重定向后映射断裂；修正为未登记不解析家族，并在 checkpoint 桶落身份指针，架构桶回退仅限旧库单条事实。
- 混合标签被子串回退并入纯 SDXL：两侧归一化命中后改为只按家族严格相等，不再走子串包含。

## Git

- 功能提交：`1246c1281d12b32feb89c332e7042619313df9d0`（本地 dev，已推送 origin/dev）。
- 远端核对：连接器 `list_commits(dev)` 最新提交即 `1246c12`，消息「feat(rules): M3 第十五切片架构标签归一化与同家族规则归并」，作者 Roy-Anan / 1538072315@qq.com。
- main 分支未改动。

## 边界

- 归一化仅覆盖 SD1.5/SDXL/Pony；其他家族待证据补充后扩展。
- 家族内冲突人工裁决、LoRA 规则组合、前端规则/家族展示界面未实现。
- 旧库（R16–R19 导入）无身份指针，多条家族事实时家族解析留空，重新导入可补齐。
