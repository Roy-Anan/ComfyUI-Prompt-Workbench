# R24 执行报告

## 1. 背景

比对层早有 `Clip Skip → clip_skip` 映射，但解析层从未从工作流提取该值；真机既有样本也不含 CLIPSetLastLayer 节点。本切片补齐该链路。

## 2. 实施步骤

1. 经 ComfyUI `/object_info/CLIPSetLastLayer` 核实：输入 `stop_at_clip_layer`，INT，default -1，min -24，max -1。
2. `workflow_service.py` 新增 `CLIP_SKIP_MARKERS` 与 `_clip_skip()`：负整数派生 `clip_skip = -value`；bool 排除；字符串尝试转 int；非负/非整数返回 None。API/UI 两段收集并写入报告 `clip_skip`（含 node_id、clip_skip、stop_at_clip_layer）。
3. `workflow_api._sampler_actuals` 合并派生 `clip_skip` 到比对 actuals。
4. `rule_compare._compare_number`：actual 为 None/空串归 `actual_missing`；其余非数值归 `actual_not_numeric`。
5. 补测试：service 3 例、compare 2 例、rules 接口 1 例。

## 3. 真机核对

脚本：`smoke_clip.py`（会话临时目录）。

- 导入 `ponyDiffusionV6XL_v6.safetensors` 档案：20 条、0 拒绝；规则 `ARCHITECTURE::Clip Skip = 2`。
- 构造 API 工作流：CheckpointLoaderSimple + CLIPTextEncode×2 + EmptyLatentImage 832×1216 + KSampler + CLIPSetLastLayer（stop_at_clip_layer=-2）。
- 报告 `clip_skip = {node_id:"8", clip_skip:2, stop_at_clip_layer:-2}`。
- compare actuals：`clip_skip=2`；Clip Skip 条目 `status=match`（rule 2，actual 2）。
- 比对计数：`unknown 18, match 2`。
- 清理后规则表 0 条。

原始样本：`samples/smoke-clip-skip.json`。

## 4. 进程与数据

- 冒烟后回收后端进程，17890 端口释放；Ollama / ComfyUI 未触碰。
- userdata 工作流副本与真机库为运行时产物，未入库；规则表已归零。

## 5. 未做

- 双 CLIP 模型跳过层数取舍、多 CLIPSetLastLayer 节点去重、VAE/CLIP 目录索引在后续切片。
