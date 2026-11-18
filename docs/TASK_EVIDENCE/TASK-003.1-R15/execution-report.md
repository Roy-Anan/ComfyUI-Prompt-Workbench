# R15 执行报告

## 目标

把旧档案里生成参数的散文值拆成可比较的结构化对象，同时保证解析不出来的内容不被臆测：原文始终保留，结构缺失即 `None`。

## 实现

1. `backend/value_normalize.py`（纯函数，无 IO/网络/存储）
   - `normalize_number_range`：纯数值 `7`→`{kind:value,value}`；`6~12`/`1.5~2`→`{kind:range,low,high}`；`30+`→`{kind:floor,low}`；其余 `None`。
   - `normalize_resolution`：抽取 `W×H`（`×`/`x`），斜杠分隔多分辨率→`{kind:resolutions,items}`；无分辨率 `None`。
   - `normalize_list`：斜杠/逗号分隔 ≥2 token→`{kind:list,items}`；单值 `None`。
   - `normalize(rule_key, raw)` 按字段名后缀路由到对应归一化器，返回 `{raw, structured}`。
2. `backend/profile_parser.py`：`candidates_to_records` 投影时调用 `value_normalize.normalize`，记录带 `structured`。
3. `backend/rule_store.py`：
   - 表新增 `structured_json TEXT`；`ensure_schema` 对旧库 `ALTER TABLE` 补列。
   - `value_json` 仍存原始裸值；结构化独立存 `structured_json`，回读记录同时给出 `value` 与 `structured`。
   - `upsert_rule` 增加 `structured` 入参；`lookup_rule`/`list_rules` 查询列同步。
4. `backend/profile_source.py`：`import_profile` 把候选 `structured` 透传给 `upsert_rule`。

## 口径对齐

- 保守解析：`SDXL 友好分辨率`、`待核实`、带备注的 `2（非 V3 独立参数）` 等不强行套数值，`structured=None`，原文留在 `value`。
- 不破坏既有接口：引擎 `record.value` 仍为裸值，结构化是附加字段，解析/冲突/未知判定口径不变。
- 纯函数可测：归一化不触达 ComfyUI/Ollama/文件系统。

## 未纳入本轮

结构化参数的前端展示与参数比对/冲突检测；architecture/global 级规则装载；逐候选勾选/驳回/差异预览；多模型/LoRA 组合；动态检索；LLM 上下文装配；版本/差异回退。
