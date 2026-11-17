# 测试结果 — TASK-003.1-R2

## 后端 pytest

命令（项目 `.venv`，工作目录 `backend/`）：

```powershell
D:\AI\ComfyUI-Prompt-Workbench-Git\.venv\Scripts\python.exe -m pytest -q
```

原始输出见同目录 `pytest-output.txt`。

结果：**57 passed, 1 warning in 7.68s**（exit 0）。

- 既有测试：`test_main.py`、`test_scripts.py` 全部通过。
- 工作流测试：`test_workflow_service.py` 全部通过（含扁平 API 识别、角色识别、白名单写入、原始文件不变、非白名单变更拒绝、原始指纹变化拒绝、未确认拒绝、UI 只读、超 20MB 拒绝等用例）。
- 唯一 warning：`StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated`，来自 FastAPI TestClient，非本轮改动引入，不影响结果。

## 前端构建

命令（工作目录 `frontend/`）：

```powershell
npm run build
```

原始输出见同目录 `frontend-build.txt`。

结果：**exit 0**。`tsc -b` 通过；Vite 5.4.21 生产构建成功，33 个模块转换完成：

```text
dist/index.html                   0.41 kB │ gzip:  0.28 kB
dist/assets/index-BPFWm_Qr.css    4.64 kB │ gzip:  1.52 kB
dist/assets/index-C4-wWkSq.js   154.92 kB │ gzip: 50.28 kB
✓ built in 864ms
```

## 语法编译检查

`python -m py_compile backend/workflow_service.py`：exit 0。

## 测试覆盖口径说明

任务书第三节列出 12 类建议回归测试。本轮 ChatGPT 仅提供了 `workflow_service.py` 完整修正版，未提供新增测试文件内容；按既定分工（测试代码由 ChatGPT 提供，豆包不自行编写测试断言），本轮未新增测试用例，沿用本机既有 `test_workflow_service.py`。既有 11 个工作流用例已覆盖其中大部分场景；以下任务书条目在既有测试中无对应用例，需后续由 ChatGPT 补充：

- 带 `nodes` 字典的兼容 API 结构识别（修正版代码已支持，既有样本为扁平结构）。
- 写入前版本快照保存的是旧 Prompt 而非新 Prompt 的显式断言。
- 重复导入、重新打开工作流时记录与内容持久化的显式断言。

未删除任何原有测试，未降低断言标准，未把扁平 API 样本改成 `nodes` 包裹格式。
