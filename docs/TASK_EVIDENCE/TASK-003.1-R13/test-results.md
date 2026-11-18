# R13 测试结果

## 后端 pytest

命令：`python -m pytest -q`（`.venv` Python 3.13.18，pytest 8.4.2）

结果：**109 passed, 1 warning in 4.79s**。原始输出见 `pytest-output.txt`。

### 新增用例（test_profile_source.py）

- `test_list_profiles_summaries`：两份样本清单身份/架构/候选数/未知字段正确，error 为空。
- `test_preview_profile_candidates`：预览记录 level/scope_key/rule_key/value/来源/可信度正确；预览后 `/api/rules` 为空（未落库）。
- `test_preview_profile_unknown_file_returns_404`：缺失档案 404。
- `test_list_missing_directory_is_empty_not_error`：目录不存在返回空清单，不报错。

## 前端构建

命令：`npm run build`（Node v22.23.2，Vite 5.4.21）

结果：exit 0，33 模块，`dist/assets/index-IXKUmsZF.js 156.95 kB`。本轮无前端改动，构建仅作回归。原始输出见 `frontend-build.txt`。

## 真机冒烟

工作台 17890 拉起（根 PID 7148 + 子进程 24176），bootstrap 换会话后：

| 步骤 | 结果 |
| --- | --- |
| GET `/api/profiles` | 200，13 份档案 |
| GET `/api/profiles/Anything_V5.txt` | 200，filename=anything-v5.safetensors，arch=SD1.5，11 候选，26 未知字段 |
| 样本记录 | `ARCHITECTURE::Base Architecture`，verified_mirror/partial |
| GET 缺失档案 | 404 Profile not found |
| GET `/api/rules`（预览后） | 200，items=0（未落库） |

快照见 `samples/smoke-profiles.json`。验收后进程树已回收（根 7148 + 子 24176），17890 释放；stopper 命中既有身份校验缺陷，按父子关系/命令行核对后手动回收并清理运行记录。
