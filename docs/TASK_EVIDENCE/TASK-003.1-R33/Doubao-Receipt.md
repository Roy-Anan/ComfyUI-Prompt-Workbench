# Doubao 回执 — TASK-003.1-R33

## 任务

M3 第二十八切片：分号两套建议分组结构化（sets，保守归 unknown）。旧档案同一字段含「示例套；指南套」两套建议，此前分号不拆、整体归 unknown；本切片把可解析双套显式分组为 `sets`，比对层仍保守归 unknown，不判定命中。

## 完成内容

- `backend/value_normalize.py`：`_split_sets` 拆套；`normalize` 多套全成功出 `sets`、任一失败整体 None；`normalize_list` 识别缺失标记返回 None。
- `backend/test_value_normalize.py`：sets 成功/失败、list 缺失标记、采样器/分辨率双套分组用例。
- `frontend/src/format.ts`：`sets` 分支递归渲染各套摘要，以 `；` 连接。
- 比对层 `rule_compare.py` 零改动；`sets` 落入既有 `structured_kind_unhandled` 分支。
- 文档：`PROJECT_STATE.md` 第 43 节、`docs/ROADMAP.md` 回填 R33。

## 口径

- 全成功才出 sets；任一子套失败整体 `structured=None`，不混并示例套与推荐套。
- sets 不参与匹配判定，避免示例值误判合规；优先级语义留后续。
- 缺失标记（未给出/待核实/待填写/未找到/暂无/none/no）不提升为推荐项。

## 自测结果

- 后端：**168 passed, 1 warning in 6.16s**。
- 前端：`tsc -b && vite build` exit 0；`index-BK2qO8n_.js 165.17 kB │ gzip 53.25 kB`，CSS 8.09 kB。
- 真机（Juggernaut_XI）：CFG/Resolution/Sampler/Steps 双套 sets 摘要正确；Scheduler `Exponential；未给出` 归 None；比对层 sets 条目全部 unknown，无 match/out_of_set 误判。截图 `screenshots/rules-sets.png`；载荷 `samples/rules-payload.json`、`samples/compare-payload.json`。
- 规则表 0 条；后端进程已回收，17890 端口释放；工作流副本已删。

## Git

- 功能提交：见下方回填。
- 回执提交：见下方回填。
- main 分支未改动。

## 边界

- 示例套/推荐套优先级语义未拍板；sets 判定留后续切片。
