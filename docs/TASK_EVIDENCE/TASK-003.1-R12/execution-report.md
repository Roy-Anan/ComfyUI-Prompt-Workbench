# R12 执行报告

## 目标

把旧 `legacy-materials/profiles/*.txt` 分节档案解析为结构化规则候选，标注来源与可信度；缺失信息记 unknown，不臆测、不直接入库。

## 实现

1. `backend/profile_parser.py`
   - `parse_profile_text(text, source_filename=None)`：按 `[SECTION]` 分节，`字段: 值` 拆分；提取顶层 filename（Exact Checkpoint Filename）、display_name、architecture（Base Architecture，剥离尾部括号备注）。
   - 标注识别：方括号 `[…]` 与无前缀标签（作者推荐/作者示例/作者说明/已核实/镜像核实/社区参考/社区经验/待核实）两路。
   - `_classify` 映射：已核实/镜像核实 → verified_mirror/partial；作者说明 → author/partial；作者推荐/作者示例 → author/authoritative；含社区 → community/unverified；其余 → unverified/unverified。
   - `_is_missing`：空值、以未给出/待填写/未找到/暂无等短语开头判缺失；范例字段内嵌「未找到/未给出/暂无」判缺失；缺失字段进 `unknown_fields`，不产候选。
   - `candidates_to_records(profile, level, scope_key)`：候选投影为规则记录形状 dict，`rule_key=SECTION::Field`、`version=legacy-1`，保留 `source_section`/`source_raw`/`note`。

## 口径对齐

- 纯只读：不写 `workbench_rule` 表、不访问 ComfyUI/Ollama、不改工作流文件；投影 dict 只供后续审核导入切片使用。
- 保守解析：散文值保留原文，不强行解析为步长/分辨率/CFG 数值；不据系列或关键词推断参数。
- 与旧 `profile_lookup.py` 口径一致：身份按完整 checkpoint 文件名，解析出的 filename 供后续精确匹配，不做模糊推断。

## 未纳入本轮

候选→规则库的审核导入与落库、三级规则实际数据装载、前端规则管理界面、多模型/LoRA 组合、冲突人工裁决、动态检索、LLM 上下文装配、版本/差异回退。
