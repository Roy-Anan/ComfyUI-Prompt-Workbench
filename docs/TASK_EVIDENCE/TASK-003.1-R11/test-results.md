# R11 测试结果

## 后端 pytest

命令：`python -m pytest -q`（`.venv` Python 3.13.18，pytest 8.4.2）

结果：**100 passed, 1 warning in 4.70s**。原始输出见 `pytest-output.txt`。

### 新增/扩展用例（test_rule_api.py）

- `test_upsert_and_delete_rule_via_api`：POST 写入后清单 1 条；DELETE 返回 removed=True；再查清单为空。
- `test_upsert_rejects_invalid_rule`：level=avatar 返回 400，清单仍为空。
- 既有：清单接口、继承解析接口、空键/坏层级 400。

## 前端构建

命令：`npm run build`（Node v22.23.2，Vite 5.4.21）

结果：exit 0，33 模块，`dist/assets/index-IXKUmsZF.js 156.95 kB`。原始输出见 `frontend-build.txt`。前端仅新增 `apiDelete`，无界面改动。

## 真机冒烟

工作台 17890 拉起（根 PID 28380 + 子进程 4648），bootstrap 换会话与 CSRF 后：

| 步骤 | 结果 |
| --- | --- |
| POST 写入 checkpoint/steps=32 | 200，回挂 level=checkpoint、value=32 |
| GET 清单 | 200，items=1 |
| GET resolve（steps,clip_skip） | 200，steps=32，unknown=[clip_skip] |
| POST level=avatar | 400 Unknown rule level |
| DELETE 该规则 | 200，removed=True |
| GET 清单 | 200，items=0 |

快照见 `samples/smoke-rules-write.json`。验收后进程树已回收（根 28380 + 子 4648），17890 释放；stopper 命中既有身份校验缺陷，按父子关系/命令行核对后手动回收并清理运行记录。
