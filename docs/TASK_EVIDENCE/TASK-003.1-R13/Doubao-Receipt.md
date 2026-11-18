# Doubao 回执 — TASK-003.1-R13

## 任务

ComfyUI Prompt Workbench，M3 第八切片：旧档案扫描清单与候选预览只读接口（本地 FastAPI + React 免安装本机 Web）。

## 执行结果

- 新增 `backend/profile_source.py`：profiles 目录扫描与单档案候选预览，目录可由 `WORKBENCH_PROFILES_DIR` 覆盖；损坏/不可读容错不抛 500。
- `main.py` 新增 `GET /api/profiles`、`GET /api/profiles/{file_name}`（404）；预览复用候选投影，不写规则库。
- 解析口径修正：IDENTITY 节只提取匹配身份，不再产生规则候选。
- 后端 pytest **109 passed**（1 条既有 StarletteDeprecationWarning）；前端 `tsc -b && vite build` exit 0（33 模块）。
- 真机闭环：13 份清单、预览 11 候选、缺失 404、预览后规则库 0 条，见 `samples/smoke-profiles.json`。

## 交付边界

- 本轮只读预览：候选审核导入落库、三级规则装载、前端档案/规则管理界面未实现。
- 未对接 Ollama 对话生成（M4）、ComfyUI 出图对接（M6）；未改动 main 分支，改动落在 dev。

## 提交信息

- 分支：`dev`
- 提交：`e959704ba1a5b776e667ff553302856e1f5bb1ee`（本地 commit，已推送 origin/dev，连接器核对远端 dev 最新即此提交）。
- 基线：`a314b37`（R12 回执回填）。
