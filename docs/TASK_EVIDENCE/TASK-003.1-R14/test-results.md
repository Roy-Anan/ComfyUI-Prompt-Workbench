# R14 测试结果

## 后端 pytest

命令：`python -m pytest -q`（`.venv` Python 3.13.18，pytest 8.4.2）

结果：**112 passed, 1 warning in 5.08s**。原始输出见 `pytest-output.txt`。

### 新增用例（test_profile_source.py）

- `test_import_profile_persists_candidates`：POST 导入 Alpha.txt，2 条 checkpoint 规则入库；清单含架构与 Steps；引擎解析 Steps=20 为 resolved。
- `test_import_missing_profile_returns_404`：导入 Nope.txt 返回 404。
- `test_import_profile_without_filename_is_rejected`：无 checkpoint 文件名档案返回 400。

## 前端构建

命令：`npm run build`（Node v22.23.2，Vite 5.4.21）

结果：exit 0，33 模块，`dist/assets/index-IXKUmsZF.js 156.95 kB`。本轮无前端改动，构建仅作回归。原始输出见 `frontend-build.txt`。

## 真机冒烟

工作台 17890 拉起（根 PID 28172 + 子进程 28304），bootstrap 换会话后：

| 步骤 | 结果 |
| --- | --- |
| 选档 Anything_V5.txt | filename=anything-v5.safetensors，预览 11 候选 |
| POST `/api/profiles/import` | 200，imported=11，rejected=0，unknown=26 |
| GET checkpoint 规则清单 | 200，items=11 |
| 解析回读 Base Architecture | 200，resolved，值 `SD1.5（SHA256 一致）` |
| 清理已导入规则 | 清单 items=0 |

快照见 `samples/smoke-import.json`。验收后进程树已回收（根 28172 + 子 28304），17890 释放；stopper 命中既有身份校验缺陷，按父子关系/命令行核对后手动回收并清理运行记录。
