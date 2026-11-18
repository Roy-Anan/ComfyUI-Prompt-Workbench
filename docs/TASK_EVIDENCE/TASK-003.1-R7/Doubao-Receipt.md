# Doubao 回执 — TASK-003.1-R7

## 任务

ComfyUI Prompt Workbench，M3 第二切片：模型身份库骨架与元数据缓存（本地 FastAPI + React 免安装本机 Web）。

## 执行结果

- 后端新增 `backend/model_identity.py`：SQLite `model_identity` 身份表，记录绝对路径/大小/mtime/可空 SHA256 与时间戳；目录索引刷新元数据，大小或 mtime 变化使缓存哈希失效；SHA256 分块流式、按需计算并缓存。
- `/api/models/catalog` 对已配置 checkpoint/lora 目录索引身份库并回挂 `identity` 摘要；无记录返回 `{known:false}`。
- 前端清单展示大小与「已校验/未哈希」身份标签。
- 后端 pytest **77 passed**（1 条既有 StarletteDeprecationWarning）；前端 `tsc -b && vite build` exit 0（33 模块）。
- 真机核对：13 checkpoint / 3 LoRA 回挂大小与未哈希状态；最小 LoRA `suyuexi.safetensors` 按需哈希成功（摘要前缀 `fedeb940e772`）；设置核对后恢复空串。

## 交付边界

- 未实现三级规则继承、规则来源/可信度/版本/回退、规则组合与冲突检测、动态检索、云端资料导入审核（后续 M3 切片）。
- 未对接 Ollama 对话生成（M4）、ComfyUI 出图任务/队列/进度/结果/输出目录索引（M6）。
- 未改动 main 分支；改动落在 dev。

## 提交信息

- 分支：`dev`
- 提交：见提交后回填（本地 commit 与 origin/dev 推送记录）。
- 基线：`d8f8778`（R6）。
