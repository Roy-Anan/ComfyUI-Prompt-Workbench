# 执行报告 — TASK-003.1-R5

## 基线

- 仓库：`D:\AI\ComfyUI-Prompt-Workbench-Git`，远端 `https://github.com/Roy-Anan/ComfyUI-Prompt-Workbench`
- 起始基线：本地 dev `52d8d3a`（领先 origin/dev 1 个提交，R4 推送受网络阻断未达远端），工作区干净；main `3084866` 未改动。
- 端口：工作台 17890，Ollama 11434，ComfyUI 8188。

## 样本

`suyuexisdxlapi.json`（用户从 ComfyUI 网页导出的 API 格式），8 节点：

- 节点 1 CheckpointLoaderSimple：`intorealismUltra_v80.safetensors`
- 节点 10 LoraLoader：`suyuexifull_c1-st6000.safetensors`，strength_model 0.7，strength_clip 0.85
- 节点 4 CLIPTextEncode：正向 Prompt
- 节点 5 CLIPTextEncode：负向 Prompt
- 节点 6 EmptyLatentImage：704 × 1024，batch 1
- 节点 7 KSampler：seed 231661496131269，steps 35，cfg 5.5，dpmpp_2m_sde / karras，denoise 1；positive→4，negative→5
- 节点 8 VAEDecode；节点 9 SaveImage（前缀 `pony_sdxl`）

## 服务端离线闭环（临时脚本，未入库）

在隔离临时数据目录用真实样本跑通：导入 → 解析 → 确认白名单 → 写回 → 重建 Store 重开 → 原始指纹不变 → 快照存写入前版本 → 非白名单篡改（改 seed）被拒。结果：全部通过。

## 代码改动

### `backend/test_workflow_service.py`

- 新增 `test_real_exported_api_workflow_full_writeback_roundtrip`：结构对齐真机样本（Checkpoint + LoRA + KSampler + EmptyLatent + VAEDecode + SaveImage，正向 4 / 负向 5），断言：
  - 格式 `api`、8 节点、可写；
  - checkpoint / lora 名与双强度识别正确；
  - 追溯到正向 4、负向 5；
  - 确认白名单后写回，2 个节点变化；
  - 重建 Store 重开后持久化文本一致；
  - 原始文件未改；版本快照与原始一致。

## 真机浏览器闭环（127.0.0.1:17890）

1. 工作台拉起（PID 22072），浏览器进入工作流工作区。
2. 上传 `suyuexisdxlapi.json`：识别为 API · 8 节点；模型节点 1、LoRA 节点 10 与强度正确；节点 4 正向、节点 5 负向。
3. 确认白名单：节点 4 正向、节点 5 负向；状态变为「已确认白名单」，编辑面板出现。
4. 正向 Prompt 末尾追加验收标记 `bench-acceptance-mark`，负向保持原样；点「写入工作副本并校验」→ 1 个节点变化，非白名单完整性校验通过。
5. 刷新页面重开工作流：标记仍在，负向未变；列表保持「已确认白名单」。
6. 文件系统核对：`original.json` 无标记、`working.json` 含标记、负向两版一致；seed / LoRA 强度 / checkpoint 名未变；`versions/` 1 份写入前快照，无标记。

## 未做（边界）

- 未向 ComfyUI 提交出图任务；未拉取历史/结果；未登记输出目录。
- 未实现 Ollama 对话生成（M4）、ComfyUI 提交/队列/进度/结果拉取（M6）。
- 未改动外部模型目录扫描与身份缓存（M3 / M8）。
