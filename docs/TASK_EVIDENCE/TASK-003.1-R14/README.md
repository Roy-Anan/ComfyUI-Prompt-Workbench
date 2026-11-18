# TASK-003.1-R14 证据目录

M3 第九切片：档案候选审核导入规则库。

## 交付物

- `backend/profile_source.py`：`import_profile()`，候选经引擎校验后 upsert 为 checkpoint 级规则；非法候选跳过记 rejected；无文件名 400。
- `backend/main.py`：`POST /api/profiles/import`（`ProfileImport`），会话/CSRF 保护，404/400 处理。
- `backend/test_profile_source.py`：导入落库与解析回读、404、无文件名拒绝 3 例。

## 切片边界

- 仅 checkpoint 级导入；architecture/global 级规则装载留后续切片。
- 整档 upsert：无逐候选勾选/驳回/差异预览；不调用 ComfyUI/Ollama。

## 验收记录

| 项 | 结果 |
| --- | --- |
| 后端 pytest | 112 passed, 1 warning（见 `pytest-output.txt`） |
| 前端构建 | tsc -b && vite build exit 0（见 `frontend-build.txt`） |
| 真机闭环 | `samples/smoke-import.json`（11 条入库 / 0 拒绝 / 解析回读 / 清理归零） |
