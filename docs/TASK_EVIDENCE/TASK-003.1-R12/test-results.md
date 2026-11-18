# R12 测试结果

## 后端 pytest

命令：`python -m pytest -q`（`.venv` Python 3.13.18，pytest 8.4.2）

结果：**105 passed, 1 warning in 4.76s**。原始输出见 `pytest-output.txt`。

### 新增用例（test_profile_parser.py）

- `test_extract_filename_display_and_architecture`：顶层身份字段提取。
- `test_missing_fields_are_unknown_without_candidates`：VAE/Clip Skip/CFG 进 unknown，不产候选。
- `test_provenance_and_confidence_mapping`：已核实→verified_mirror/partial；作者说明→author/partial；作者推荐→author/authoritative。
- `test_candidates_to_records_shape`：投影 dict 含 level/scope_key/rule_key/source_raw；缺失字段不入记录。
- `test_community_note_maps_to_unverified`：社区参考→community/unverified。

## 前端构建

命令：`npm run build`（Node v22.23.2，Vite 5.4.21）

结果：exit 0，33 模块，`dist/assets/index-IXKUmsZF.js 156.95 kB`。本轮无前端改动，构建仅作回归。原始输出见 `frontend-build.txt`。

## 真实档案盘点

对 `legacy-materials/profiles/` 全部 13 份 `.txt` 跑解析：13 份均解析出完整 checkpoint 文件名；合计 **288** 条候选、**270** 个未知字段；架构标签剥离尾部括号备注。明细见 `samples/profile-parse-summary.json`（含每份候选数、未知字段清单与两条记录形状样本）。
