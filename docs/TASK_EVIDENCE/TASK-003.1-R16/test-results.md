# R16 测试结果

## 后端 pytest

命令：`python -m pytest -q`（`.venv` Python 3.13.18，pytest 8.4.2）

结果：**119 passed, 1 warning in 5.23s**。原始输出见 `pytest-output.txt`。

### 变更/新增用例

- `test_candidates_to_records_shape`（test_profile_parser.py）：ARCHITECTURE 节记录 level=architecture、scope=SDXL 1.0；其余记录 level=checkpoint、scope=checkpoint 文件名。
- `test_import_profile_persists_candidates`（test_profile_source.py）：Steps 落 checkpoint 作用域；Base Architecture 落 architecture 作用域 SDXL 1.0；checkpoint 清单不再含架构字段。
- `test_import_architecture_field_without_label_is_rejected`（新增）：无 Base Architecture 时，Model Type 记入 rejected，Steps 正常入库（imported=1）。

## 前端构建

命令：`npm run build`（Node v22.23.2，Vite 5.4.21）

结果：exit 0，33 模块，`dist/assets/index-IXKUmsZF.js 156.95 kB`。本轮无前端改动，构建仅作回归。原始输出见 `frontend-build.txt`。

## 真机冒烟

工作台 17890 拉起（根 PID 25812 + 子进程 21292），bootstrap 换会话后：

| 步骤 | 结果 |
| --- | --- |
| 选档 Anything_V5.txt | filename=anything-v5.safetensors，架构标签 SD1.5，预览 11 候选 |
| POST `/api/profiles/import` | 200，imported=11，rejected=0 |
| checkpoint 作用域清单 | 9 条（CONFIDENCE/GENERATION SETTINGS/MODEL BEHAVIOR/PROMPT STYLE） |
| architecture 作用域清单 | 2 条，scope=SD1.5（Base Architecture、Model Type） |
| checkpoint 上下文解析架构字段 | unknown（架构规则不泄漏进 checkpoint 作用域） |
| 清理两类规则 | checkpoint=0，architecture=0 |

快照见 `samples/smoke-levels.json`。验收后进程树已回收（根 25812 + 子 21292），17890 释放；stopper 命中既有身份校验缺陷，按父子关系/命令行核对后手动回收并清理运行记录。
