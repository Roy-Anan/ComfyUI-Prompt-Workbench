# TASK-003.1-R33 M3 第二十八切片：分号两套建议分组结构化（sets，保守归 unknown）

## 范围

旧档案同一字段常含「作者示例；作者指南」两套建议（如 Steps `35；25~40`、CFG `4；4~6`）。此前分号套不拆，任一无法解析则整体 `structured=None`。本切片在归一化层按分号拆套：两套均可解析时产出 `sets` 分组结构；任一失败整体保持 None。比对层 `sets` 暂归 `unknown`（`structured_kind_unhandled`），不做命中判定；前端摘要递归渲染各套。

## 改动文件

- `backend/value_normalize.py`：新增 `_split_sets`；`normalize` 多套分支；`normalize_list` 识别缺失标记（未给出/待核实/待填写/未找到/暂无/none/no）返回 None。
- `backend/test_value_normalize.py`：sets 成功/失败、list 缺失标记、采样器/分辨率双套分组用例。
- `frontend/src/format.ts`：`formatStructured` 新增 `sets` 分支，各套递归摘要以 `；` 连接。
- 比对层 `rule_compare.py` 零改动：`sets` 落入既有 `structured_kind_unhandled` 分支归 unknown。

## 口径

- 全成功才出 `sets`；任一子套解析失败 → 整体 `structured=None`，不混并示例套与推荐套。
- `sets` 不参与匹配判定，避免把示例值误判为合规；示例套/推荐套优先级语义留后续切片。
- 缺失标记在列表归一化层同样视为不可用，不把「未给出」提升为推荐项。

## 验收结论

- 后端 pytest：168 passed, 1 warning in 6.16s。
- 前端构建：exit 0；`index-BK2qO8n_.js 165.17 kB`（gzip 53.25 kB），CSS 8.09 kB。
- 真机（Juggernaut_XI）：CFG/Resolution/Sampler/Steps 双套 sets 摘要正确；Scheduler `Exponential；未给出` 归 None；比对层 sets 条目全部 unknown，无误判。
- 清理后规则表 0 条。

## 证据清单

- `samples/rules-payload.json`：sets 规则记录。
- `samples/compare-payload.json`：比对 verdict（sets 归 unknown）。
- `screenshots/rules-sets.png`：规则库 sets 摘要。
- `pytest-output.txt` / `frontend-build.txt` / `git-diff.md` / `git-diff-raw.txt` / `known-issues.md`。
