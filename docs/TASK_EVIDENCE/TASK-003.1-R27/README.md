# TASK-003.1-R27 证据目录

M3 第二十二切片：多采样器组逐组比对。

## 交付物

- `backend/rule_compare.py`：`compare_workflow` 新增 `sampler_group_comparisons`，每组用公共事实叠加本组 params 独立比对；`_count` 抽为共用函数。
- `backend/test_workflow_rules.py`：双组工作流逐组结论断言（首组 match、次组 out_of_range，分组计数独立）。
- `frontend/src/WorkflowWorkbench.tsx`：`GroupComparison` 类型与「逐采样器组比对」分组卡片。
- `frontend/src/styles.css`：分组卡片样式。

## 口径

- 顶层 `comparisons` / `counts` 仍对应首组；逐组结论在 `sampler_group_comparisons`。
- 组间参数不合并、不替选；跨组冲突裁决不在本切片。

## 验收记录

| 项 | 结果 |
| --- | --- |
| 后端 pytest | 164 passed, 1 warning（见 `pytest-output.txt`） |
| 前端构建 | tsc -b && vite build exit 0（见 `frontend-build.txt`） |
| 真机浏览器 | `screenshots/compare-group1.png`、`compare-group2.png`；载荷 `samples/compare-payload.json` |
