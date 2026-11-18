# R15 测试结果

## 后端 pytest

命令：`python -m pytest -q`（`.venv` Python 3.13.18，pytest 8.4.2）

结果：**118 passed, 1 warning in 5.36s**。原始输出见 `pytest-output.txt`。

### 新增用例（test_value_normalize.py，6 passed）

- `test_number_range_and_value`：range / value / floor / 小数范围。
- `test_number_unparseable_stays_none`：散文与待核实值回退 `None`。
- `test_resolution_list`：多分辨率解析；非分辨率散文 `None`。
- `test_sampler_list`：斜杠分隔采样器列表。
- `test_normalize_routes_by_field_key`：按字段名路由；失败保留 raw。
- `test_candidate_records_carry_structured`：候选记录带 `structured`，Steps/Resolution/Sampler 结构正确。

## 前端构建

命令：`npm run build`（Node v22.23.2，Vite 5.4.21）

结果：exit 0，33 模块，`dist/assets/index-IXKUmsZF.js 156.95 kB`。本轮无前端改动，构建仅作回归。原始输出见 `frontend-build.txt`。

## 真机冒烟

工作台 17890 拉起（根 PID 26844 + 子进程 26592），bootstrap 换会话后：

| 步骤 | 结果 |
| --- | --- |
| 选档 IntoRealism_Ultra_V8.txt | filename=intorealismUltra_v80.safetensors，预览 16 候选 |
| POST `/api/profiles/import` | 200，imported=16，rejected=0 |
| GET checkpoint 规则清单 | 200，items=16 |
| Steps | raw `6~12` → range low 6 high 12 |
| CFG | raw `1.5~2` → range low 1.5 high 2 |
| Resolution | raw `896×1152 / 832×1216` → resolutions 两项 |
| Sampler | raw `Euler A Karras / Exponential` → list 两项 |
| 清理已导入规则 | 清单 items=0 |

快照见 `samples/smoke-structured.json`。验收后进程树已回收（根 26844 + 子 26592），17890 释放；stopper 命中既有身份校验缺陷，按父子关系/命令行核对后手动回收并清理运行记录。
