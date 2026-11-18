# Doubao 回执 — TASK-003.1-R24

## 任务

M3 第十九切片：Clip Skip 实际参数链路。比对层早有 `Clip Skip → clip_skip` 映射，但解析层从未提取该值；本切片打通 CLIPSetLastLayer 节点到 actuals 的链路。

## 完成内容

- `backend/workflow_service.py`：`CLIP_SKIP_MARKERS` + `_clip_skip()`；读取 `stop_at_clip_layer`，负整数派生 `clip_skip = -value`；API/UI 两段收集并写入报告。
- `backend/workflow_api.py`：actuals 合并派生 `clip_skip`。
- `backend/rule_compare.py`：数值比对区分缺值 `actual_missing` 与非数值 `actual_not_numeric`。
- 测试：service 3 例、compare 2 例、rules 接口 1 例。
- 文档：`PROJECT_STATE.md` 第 34 节、`docs/ROADMAP.md` 回填 R24。

## 口径

- 节点 `stop_at_clip_layer` 取值域 -24…-1（ComfyUI object_info 核实）；规则层为正数跳过层数，换算 `clip_skip = -stop_at_clip_layer`。
- bool 排除；字符串尝试转 int；非负 / 非整数 / 缺节点不换算，留 None，比对归 unknown。

## 自测结果

- 后端：**163 passed, 1 warning in 5.87s**。
- 前端：`tsc -b && vite build` exit 0；`index-IXKUmsZF.js 156.95 kB`。
- 真机闭环（`samples/smoke-clip-skip.json`）：
  - 导入 PonyDiffusion 档案 20 条、0 拒绝；规则 `ARCHITECTURE::Clip Skip = 2`。
  - 构造工作流 CLIPSetLastLayer -2 → 报告 clip_skip 2；actuals `clip_skip=2`；比对 `status=match`。
  - 计数 unknown 18 / match 2；清理后规则表 0 条。

## Git

- 功能提交：`09204364e063cfa38d93b137c31012e5b161b416`（本地 dev，已推送 origin/dev）。
- 远端核对：连接器 `list_commits(dev)` 最新提交即 `0920436`，消息「feat(rules): M3 第十九切片 Clip Skip 实际参数链路」，作者 Roy-Anan / 1538072315@qq.com。
- main 分支未改动。

## 边界

- 多 CLIPSetLastLayer 节点取舍、双 CLIP 模型两侧层数一致性未实现；真机暂无原生含该节点样本，本轮基于构造 API 样本闭环。
