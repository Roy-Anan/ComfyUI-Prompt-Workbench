# Doubao 回执 — TASK-003.1-R5（原始回执，未摘录润色）

## 一句话结论

用用户从 ComfyUI 导出的真实 **API 格式**样本 `suyuexisdxlapi.json`，在真机跑通工作台写入闭环：导入识别 → 白名单确认 → 写回工作副本 → 完整性校验 → 刷新重开持久化，原始文件未改、版本快照保存写入前版本。后端 **64 passed**，前端构建 **exit 0**。未向 ComfyUI 提交出图任务。

## 执行前基线

- 仓库：`D:\AI\ComfyUI-Prompt-Workbench-Git`，远端 `https://github.com/Roy-Anan/ComfyUI-Prompt-Workbench`
- 本地 dev `52d8d3a`（R4，领先 origin/dev 1 个提交，推送受网络阻断未达远端），工作区干净
- main：`3084866aa85595133c7a1179b15ddd71e659d8f3`，未合并、未改动
- 工作台版本 `0.1.0-dev.5`；Python 3.13.18；Node v22.23.2

## 本轮做了什么

### 1. 样本判定与服务端离线闭环

- `suyuexisdxlapi.json` 为标准 API prompt：顶层节点号 → `class_type` + `inputs`，连线 `["节点号", 槽位号]`；8 节点。
- 在隔离临时数据目录用真实样本跑通：导入 → 解析（正向 4、负向 5，Checkpoint 节点 1，LoRA 节点 10，强度 0.7/0.85）→ 确认白名单 → 写回 → 重建 Store 重开 → 原始指纹不变 → 快照存写入前版本 → 篡改 seed 被拒。全部通过。

### 2. 回归测试（`backend/test_workflow_service.py`，新增 1 例）

- `test_real_exported_api_workflow_full_writeback_roundtrip`：结构对齐真机样本，断言格式/节点数/可写、模型与 LoRA 识别、角色追溯、写回变化数、重开持久化、原始未改、快照与原始一致。

### 3. 真机浏览器闭环（`http://127.0.0.1:17890`，PID 22072）

- 上传 API 样本：识别为 API · 8 节点；节点 1 `intorealismUltra_v80.safetensors`；节点 10 `suyuexifull_c1-st6000.safetensors`，0.7 / 0.85；节点 4 正向、节点 5 负向。
- 确认白名单：4 正向、5 负向；状态「已确认白名单」。
- 正向末尾追加验收标记 `bench-acceptance-mark`，负向保持原样；写入 → 1 个节点变化，非白名单完整性校验通过。
- 刷新重开：标记仍在，负向未变，列表保持已确认。
- 文件系统核对：`original.json` 无标记；`working.json` 含标记；负向两版一致；seed / LoRA 强度 / checkpoint 名未变；`versions/` 1 份写入前快照，无标记。

## 测试与构建结果

- 后端：`.venv\Scripts\python.exe -m pytest -q` → **64 passed, 1 warning in 2.68s**，exit 0。
  - 警告：`StarletteDeprecationWarning`（既有遗留，非本轮引入）。
- 前端：`npm run build`（`tsc -b && vite build`）→ **exit 0**，33 modules，✓ built in 517ms。
- 原始输出：`pytest-output.txt`、`frontend-build.txt`。

## 明确未完成 / 未验证

- 未向 ComfyUI 提交出图任务；未跟踪队列/进度；未拉取生成历史与图片；未登记输出目录（M6）。
- 未实现 Ollama 模型选择、参数配置、候选生成与结构化验证（M4）。
- 外部模型目录扫描、身份缓存未做（M3 / M8）；`storage.checkpoint`、`storage.lora` 仍为空串。
- 指纹规范化偏严格、并发写锁、前端星号纯文本渲染、Python 3.12 兼容性、显存阈值等待既有 backlog 未动。
- R4 `52d8d3a` 与本轮 R5 改动尚未推送到远端 dev；本机 GitHub 直连被重置/超时，本地提交与证据已落盘，待网络恢复后推送。

## 改动文件

- 修改：`backend/test_workflow_service.py`（+111 行）
- 新增证据：`docs/TASK_EVIDENCE/TASK-003.1-R5/`（README、Doubao-Receipt、execution-report、test-results、environment-report、git-diff、git-diff-raw.txt、known-issues、pytest-output.txt、frontend-build.txt、samples/、screenshots/ 三张、logs/）

## 环境

- Windows 本机 ROY；Python 3.13.18（项目 `.venv`）；pytest 8.4.2；Node v22.23.2；npm 10.9.8；Vite 5.4.21。
- ComfyUI 0.30.2（内嵌 Python 3.13.11，8188）；Ollama 11434 在线；工作台 17890。
