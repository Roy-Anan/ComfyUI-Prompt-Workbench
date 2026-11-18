# R20 执行报告

## 目标

旧档案底座标签取值混杂（`SDXL`、`SDXL 1.0`、`Pony / SDXL 系`、`微调自 IL-XL` 等）。本切片把同义变体归到规范家族，使同一家族模型能互相继承架构规则；混合/派生标签保守隔离，不强行并入；未识别标签不猜家族。

## 改动

### 后端

- `architecture_normalize.py`（新增）
  - `normalize(label)`：返回 `raw`/`canonical`/`family`/`mixed`/`matched`。
  - `same_family(a, b)`：两侧都识别且规范家族相同才为真。
  - 关键词匹配：SD1.5、SDXL、Pony；派生标记（illustrious/IL-XL/微调自/派生/混合）置 `mixed`。
- `rule_store.py`
  - `_architecture_label()`：优先 checkpoint 桶 `IDENTITY::Base Architecture` 指针；回退 `ARCHITECTURE::Base Architecture`；旧库架构桶仅在恰好一条家族事实时使用，多条不随机挑选。
  - `_architecture_scope_matches()`：两侧都识别按规范家族严格相等；仅一侧识别不猜；都未识别才回退相等/前缀/包含。
  - `context_for_checkpoint()`：未登记模型家族留空；架构规则按家族归并；返回 `architecture_family`、`architecture_label`。
- `profile_parser.py`：ARCHITECTURE 节 Base Architecture 事实除架构桶记录外，补一条 checkpoint 桶身份指针 `IDENTITY::Base Architecture`，保留原值标签。
- `rule_prompt.py`：registered/unregistered 载荷都透传 `architecture_family`、`architecture_label`。
- `workflow_api.py`：三处未登记占位补家族/标签字段。

## 过程修正

- 首跑真机：未登记的 intorealismUltra 被挂上 `Pony / SDXL 系` 标签。根因是 R16 把 Base Architecture 重定向到架构桶后，checkpoint↔家族映射断裂；多份档案导入后架构桶有多条家族事实，跨桶回退随机取到无关家族。
  - 修正一：未登记 checkpoint 不再解析架构家族。
  - 修正二：导入时在 checkpoint 桶落身份指针，上下文优先读本模型指针；架构桶回退仅限旧库单条事实。
- 混合标签 `Pony / SDXL 系` 被子串回退并入纯 SDXL：两侧归一化命中后改为只按家族严格相等，不再走子串包含。

## 真机过程

1. 导入三份档案：huslyorealismxl（SDXL，19 条）、intorealismUltra（SDXL 1.0，17 条）、ponyDiffusionV6XL（Pony / SDXL 系，20 条）；0 拒绝。
2. 重新导入 R5 API 样本（intorealismUltra_v80）。
3. 上下文：status=registered，family=SDXL，label=SDXL 1.0；架构 scope 纳入 `SDXL` 与 `SDXL 1.0`，未纳入 `Pony / SDXL 系`；提示载荷 17 字段。
4. 清理后规则表 0 条。

## 结论

同义变体同家族继承生效；混合/派生标签与未识别标签被隔离；家族归属只来自本模型登记的身份指针，不跨模型猜测。
