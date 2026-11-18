# R13 执行报告

## 目标

在 R12 纯解析器之上，提供档案清单与候选预览的只读 HTTP 入口，供后续审核导入切片使用；本轮不把候选写入规则库。

## 实现

1. `backend/profile_source.py`
   - `profiles_dir()`：默认 `<repo>/legacy-materials/profiles`，`WORKBENCH_PROFILES_DIR` 覆盖。
   - `list_profiles()`：逐份解析汇总 file/filename/display_name/architecture/candidates/unknown_fields；单文件 `OSError/UnicodeDecodeError/ValueError` 记 `error`，不中断清单。
   - `preview_profile(file_name)`：解析单份并投影候选记录；文件缺失抛 `FileNotFoundError` 交接口层转 404；文件名取 `Path.name` 防目录穿越。
2. `backend/main.py`
   - `GET /api/profiles`：返回 `{items: [...]}`。
   - `GET /api/profiles/{file_name}`：返回身份、未知字段与候选记录；404。
3. `backend/profile_parser.py`：IDENTITY 节仅提取 filename/display_name，不再作为规则候选产出。

## 口径对齐

- 只读：预览接口不调用 `rule_store.upsert_rule`，不写库；真机冒烟确认预览后规则库 0 条。
- 容错：目录不存在返回空清单；单份损坏不拖垮整体清单。
- 与 R12 一致：缺失字段记 unknown 不产候选；来源/可信度沿用解析器映射。

## 未纳入本轮

候选审核导入落库、三级规则实际数据装载、前端档案/规则管理界面、参数结构化拆分、多模型/LoRA 组合、冲突裁决、动态检索、LLM 上下文装配、版本/差异回退。
