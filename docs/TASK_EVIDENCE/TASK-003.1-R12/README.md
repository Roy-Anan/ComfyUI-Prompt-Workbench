# TASK-003.1-R12 证据目录

M3 第七切片：旧 profiles 文本解析器与来源/可信度标注映射。

## 交付物

- `backend/profile_parser.py`：分节文本 → `RuleCandidate` / `ParsedProfile`；标注映射；缺失判定；`candidates_to_records` 投影。
- `backend/test_profile_parser.py`：身份提取、缺失不产候选、标注映射、记录形状、社区标注 5 例。

## 切片边界

- 纯只读解析层：不写规则库、不调 ComfyUI/Ollama、不回写工作流；候选仅投影成规则记录形状 dict，持久化留后续切片。
- 保守口径：散文值保留原文，不强行拆成步长/分辨率/CFG 数值；缺失字段记 unknown，不补默认。

## 验收记录

| 项 | 结果 |
| --- | --- |
| 后端 pytest | 105 passed, 1 warning（见 `pytest-output.txt`） |
| 前端构建 | tsc -b && vite build exit 0（见 `frontend-build.txt`） |
| 真实 13 份档案盘点 | `samples/profile-parse-summary.json`（288 候选 / 270 未知字段） |
