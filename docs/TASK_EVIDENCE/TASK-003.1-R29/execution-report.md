# R29 执行报告

## 1. 背景

R25 已收口多采样器组的保守标注（顶层取首组、全组列表），但 latent 尺寸与 Clip Skip 解析段仍用 `if latent is None` / `if clip_skip is None` 只保留首个命中节点，多节点工作流中其余节点被静默丢弃。本切片沿用 R25 范式，把这两类节点也全量列出。

## 2. 实施步骤

1. `workflow_service.py` API 段与 UI 段各收集 `latent_nodes`、`clip_skip_nodes`：命中节点先构造 entry 追加进列表，`if latent is None` / `if clip_skip is None` 时再赋顶层；两段 return dict 新增两列表字段。
2. `workflow_api._sampler_actuals`：在顶层 latent/clip_skip 注入后，透传 `latent_node_count` + `latent_nodes`（node_id/width/height）与 `clip_skip_node_count` + `clip_skip_nodes`（node_id/clip_skip）；旧 report 无列表字段时计数缺省。
3. 测试 `test_workflow_service.py` 新增双 latent（832×1216、768×1152）、双 CLIPSetLastLayer（stop -2、-3）用例，断言顶层取首、列表全量、clip_skip 序列 [2, 3]。
4. 前端比对面板摘要区：计数 >1 时显示保守提示，说明结论取首个、其余节点未参与比对。

## 3. 真机核对

- 前置：精确匹配导入 `ponyDiffusionV6XL_v6.safetensors` 档案 20 条，0 拒绝。
- 构造 API 工作流：节点 6 EmptyLatentImage 832×1216、节点 10 EmptyLatentImage 768×1152；节点 8 CLIPSetLastLayer stop -2、节点 11 CLIPSetLastLayer stop -3；KSampler steps 25 cfg 7.0。
- 解析事实：顶层 latent=节点 6；`latent_nodes`=[6, 10]；顶层 clip_skip=节点 8（2）；`clip_skip_nodes`=[8(2), 11(3)]。
- 比对：registered，计数 无法判定 17 / 匹配 2 / 不在集合 1；Clip Skip 2=2 匹配、Steps 25=25 匹配；Sampler euler 不在集合。
- 浏览器截图 `screenshots/compare-multi-nodes.png`，两条多节点提示可见；载荷 `samples/compare-payload.json`。
- 清理后规则表 0 条。

## 4. 排查记录

- 首轮真机比对误报 unregistered：清理/导入脚本用文件名子串 `"pony" in filename` 选择档案，命中了同名族的 `autismmixSDXL_autismmixPony.safetensors`。改为按 `filename == ponyDiffusionV6XL_v6.safetensors` 精确匹配后 registered。后端解析与匹配链路无缺陷。

## 5. 进程与数据

- 验收后回收后端进程（根 PID 17420 + uvicorn 子进程 17400），17890 释放；Ollama / ComfyUI 未触碰。
- userdata 工作流副本与真机库为运行时产物，未入库；规则表已归零。

## 6. 未做

- 多 latent / 多 CLIP 链路的节点取舍规则、跨节点冲突裁决与逐节点比对，留后续切片。
