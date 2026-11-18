# R33 测试结果

## 后端 pytest

- 命令：`backend/  python -m pytest -q`
- 结果：**168 passed, 1 warning in 6.16s**
- 新增用例：双套全成功出 sets（Steps/CFG/Sampler/Resolution）；双套任一失败整体 None；list 缺失标记归 None。
- 遗留 `StarletteDeprecationWarning` 与本切片无关。
- 原始输出：`pytest-output.txt`

## 前端构建 / 类型检查

- 命令：`frontend/  npm run build`（`tsc -b && vite build`）
- 结果：exit 0
- 产物：`index-BK2qO8n_.js 165.17 kB │ gzip 53.25 kB`，CSS 8.09 kB
- 原始输出：`frontend-build.txt`

## 真机冒烟（浏览器 + API 只读验收）

| 检查点 | 结果 |
| --- | --- |
| 双套数值/范围分组 sets | 通过：Steps `35；25~40`、CFG `4；4~6` |
| 双套分辨率/采样器分组 sets | 通过：`samples/rules-payload.json` |
| 缺失标记套整体归 None | 通过：Scheduler `Exponential；未给出` |
| 比对层 sets 归 unknown | 通过：`structured_kind_unhandled`，无 match/out_of_set；`samples/compare-payload.json` |
| 前端 sets 摘要渲染 | 通过：`screenshots/rules-sets.png` |
| 清理后规则表计数 0 | 通过 |
