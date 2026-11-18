# Doubao 回执 — TASK-003.1-R8

## 任务

ComfyUI Prompt Workbench，M3 第三切片：同 SHA256 多路径身份归并（本地 FastAPI + React 免安装本机 Web）。

## 执行结果

- 身份库新增摘要归并：同类别内相同 SHA256 的多副本映射同一身份组；`identity_group` 返回 `identity_key`（`category:digest`）、摘要与副本列表；`identity_summary` 回挂身份键、副本数与副本路径。未哈希文件身份键为空，不做哈希推断。
- 后端 pytest **80 passed**（1 条既有 StarletteDeprecationWarning）；前端 `tsc -b && vite build` exit 0（33 模块）。
- 真机核对：`suyuexi.safetensors` 哈希后身份键 `lora:fedeb940…`，`copy_count=1`（本机无重复副本）；清单摘要回挂归并字段；设置核对后恢复空串。

## 交付边界

- 归并仅按类别内摘要匹配；跨类别不合并；文件移动后按身份重新定位留后续切片。
- 规则继承、规则来源/可信度/版本/回退、规则组合与冲突检测、动态检索、云端资料导入审核未实现。
- 未对接 Ollama 对话生成（M4）、ComfyUI 出图对接（M6）；未改动 main 分支，改动落在 dev。

## 提交信息

- 分支：`dev`
- 提交：见提交后回填（本地 commit 与 origin/dev 推送记录）。
- 基线：`4e71bbc`（R7）。
