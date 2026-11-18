# R10 测试结果

## 后端 pytest

命令：`python -m pytest -q`（`.venv` Python 3.13.18，pytest 8.4.2）

结果：**98 passed, 1 warning in 4.48s**。原始输出见 `pytest-output.txt`。

### 新增用例

`test_rule_store.py`（7 passed）：upsert 往返、同三元组覆盖、JSON 列表往返、按层级/作用域过滤、删除、非法记录拒绝、存储规则接入引擎解析。

`test_rule_api.py`（3 passed）：规则清单接口、继承解析接口（checkpoint=32、clip_skip unknown）、空键/坏层级 400。

## 前端构建

命令：`npm run build`（Node v22.23.2，Vite 5.4.21）

结果：exit 0，33 模块，`dist/assets/index-IXKUmsZF.js 156.95 kB`。原始输出见 `frontend-build.txt`。本轮无前端代码改动。

## 真机冒烟

工作台 17890 拉起（PID 13264 根 + 9140 子），bootstrap 换会话后：

| 接口 | 结果 |
| --- | --- |
| `GET /api/health` | 200，app_id 正常 |
| `GET /api/rules` | 200，items=0（空库） |
| `GET /api/rules/resolve?level=global&keys=steps,cfg` | 200，unknown=[steps,cfg]，conflicts=[] |
| `level=avatar` | 400 Unknown rule level |
| `keys=` | 400 At least one rule key is required |

快照见 `samples/smoke-rules.json`。验收后进程树已回收，17890 释放；stopper 命中既有身份校验缺陷，按命令行/可执行路径/工作目录核对后手动回收子进程 9140 并清理运行记录。
