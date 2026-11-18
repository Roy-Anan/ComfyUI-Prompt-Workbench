# R22 执行报告

## 目标

R19 比对链路中，Resolution 规则此前与 list 一样按字符串包含匹配，未对接工作流实际 latent 宽高。本切片从工作流提取 latent 节点尺寸，并让 Resolution 结构化规则与实际 (宽,高) 做整数集合保守比对。

## 改动

### 后端

- `workflow_service.py`
  - 新增 `LATENT_MARKERS = ("LatentImage",)` 与 `_latent_size(inputs)`：取 width/height 标量（int/float/可转 int 的字符串），排除 bool；两者有效返回 `{"width","height"}`，否则 None。
  - API / UI 两段解析遍历节点时识别 latent 节点，取首个有效尺寸写入报告 `latent`（含 node_id）。
- `workflow_api.py`
  - `_sampler_actuals`：先合并首个采样器组 params，再叠加 latent width/height 供比对层使用。
- `rule_compare.py`
  - Resolution 字段走专用 `_compare_resolutions`：实际宽高任一缺失/非数值归 unknown/actual_missing；规则 items 归一为整数尺寸集合；实际 (w,h) 在集合内 match，否则 out_of_set。
  - `resolutions` 不再复用字符串 list 匹配。

## 过程核对

- 真机 R5 API 样本：节点 6 `EmptyLatentImage`，width 704、height 1024、batch_size 1。
- 旧档案 Resolution 样本：`[作者推荐] 896×1152 / 832×1216`（IntoRealism）→ resolutions 两项；`SDXL 友好分辨率`、`未给出（…）` 类散文 structured=None，保持 unknown。

## 真机过程

1. 启动后端，导入 IntoRealism 档案 17 条、0 拒绝。
2. 规则库核对：Resolution value `896×1152 / 832×1216`，structured resolutions 两项。
3. 导入 R5 API 样本：报告 latent `{node_id:6, width:704, height:1024}`，analysis.json 持久化并回读一致。
4. compare：actuals 含 width 704 / height 1024；Resolution 实际 704×1024 不在规则集合 → out_of_set（保守判定，不按比例或近似推断匹配）。
5. 清理后规则表 0 条。

## 结论

Resolution 规则现在基于可读的实际 latent 尺寸判定；读不到尺寸或规则无结构化时归 unknown，未引入近似/比例猜测。
