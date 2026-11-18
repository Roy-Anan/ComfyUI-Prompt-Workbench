# R33 执行报告

## 任务

旧档案同一字段的分号双套建议（示例套 + 指南套）此前不拆分，整体归 unknown。本切片把可解析的双套显式分组为 `sets` 结构，同时保持比对保守：`sets` 不判定命中，优先级语义留后续。

## 实施步骤

1. `value_normalize` 新增 `_split_sets`，按 `；`/`;` 拆套并去空。
2. `normalize`：单套走既有 normalizer；多套逐套解析，全部非 None 才产出 `{"kind":"sets","items":[...]}`，任一失败整体 None。
3. `normalize_list` 补缺失标记识别：`未给出/待核实/待填写/未找到/暂无/none/no` 开头的 token 视为不可用，返回 None，避免把缺失文案提升为推荐列表项。
4. `format.ts` 新增 `sets` 分支：递归渲染各套摘要，以 `；` 连接。
5. 补后端单测；后端回归、前端构建；真机导入 Juggernaut_XI 核对 sets 分组与摘要；构造工作流跑比对确认 sets 归 unknown。
6. 清理导入规则与工作流副本，回收后端进程。

## 真机结果（Juggernaut_XI）

| 字段 | raw | structured |
| --- | --- | --- |
| CFG | `4； 4~6` | sets：value 4；range 4~6 |
| Resolution | `832×1216； 1024×1024 / 832×1216 / 1216×832` | sets：两套 resolutions |
| Sampler | `DPM++ 2M SDE； DPM++ 2M Karras` | sets：两套 list |
| Scheduler | `Exponential； 未给出` | None（第二套缺失标记） |
| Steps | `35； 25~40` | sets：value 35；range 25~40 |

比对 verdict：CFG/Resolution/Sampler/Steps 均 `unknown / structured_kind_unhandled`；Scheduler `unknown / rule_not_structured`；计数 `unknown: 20`，无 match/out_of_set 误判。

## 进程回收

- 父 PID 24180、uvicorn 子 PID 21104 已回收，17890 释放；规则表 0 条；工作流副本 `8ffc01f9…` 已删。
