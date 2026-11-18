# R23 执行报告

## 目标

R21 统一对参数值剥离尾部括号备注后再解析。该口径对数值/列表字段正确，但误伤 Resolution：括号备注内往往正是分辨率本体（如 `系列普通版友好分辨率（768×1152 / 648×1152 / 864×1152，待核对 V3）`），剥离后无尺寸可提取，structured=None。本切片让 Resolution 回到原始文本提取，其余字段维持备注剥离。

## 改动

### 后端

- `value_normalize.py`
  - `normalize_resolution`：基于传入文本 findall `W×H`；重复 (宽,高) 按首次出现去重。
  - `normalize()`：`Resolution` 字段以原始 `raw` 喂 normalizer；其余字段仍以剥离尾部备注的 `cleaned` 喂 normalizer；`raw` 始终保留原值。

## 过程核对

- 真机样本：HuslyoRealismSDXL_v3 档案，Resolution `系列普通版友好分辨率（768×1152 / 648×1152 / 864×1152，待核对 V3）`；Clip Skip `2（非 V3 独立参数）`；Steps `30~32`；Scheduler `Karras`。
- 对照口径：Resolution 尺寸在括号内，必须保留；Clip Skip 核心数值 2 在括号外，备注应剥离。

## 真机过程

1. 启动后端，导入 HuslyoRealismSDXL_v3 档案 20 条、0 拒绝。
2. Resolution 提取括号内三组 `{768×1152, 648×1152, 864×1152}`，structured=resolutions。
3. 同档案 Clip Skip `2（非 V3 独立参数）`→value 2；Steps `30~32`→range；Scheduler `Karras`→单元素 list。
4. 清理后规则表 0 条。

## 结论

Resolution 与数值/列表两条解析路径各自按口径工作，互不误伤；括号内非尺寸备注仍留在 raw，未参与结构化。
