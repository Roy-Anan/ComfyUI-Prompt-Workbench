# R31 测试结果

## 后端 pytest

- 命令：`backend/  python -m pytest -q`
- 结果：**165 passed, 1 warning in 6.04s**
- 说明：本切片后端零改动；165 条既有回归全部通过。遗留 `StarletteDeprecationWarning` 与本切片无关。
- 原始输出：`pytest-output.txt`

## 前端构建 / 类型检查

- 命令：`frontend/  npm run build`（`tsc -b && vite build`）
- 结果：exit 0
- 产物：`index-D68eGJQw.js 165.08 kB │ gzip 53.22 kB`，CSS 8.09 kB
- 原始输出：`frontend-build.txt`

## 真机冒烟（浏览器只读验收）

| 检查点 | 结果 |
| --- | --- |
| value 摘要（CFG 5、Clip Skip 2） | 通过 |
| range 摘要（Steps 30~32、CFG 4~6） | 通过 |
| floor 摘要（Steps ≥30） | 通过 |
| resolutions 摘要（896×1152 / 832×1216） | 通过 |
| list 摘要（采样器/调度器以 `/` 连接） | 通过 |
| 比对面板规则列：数值/分辨率/列表/下限 | 通过 |
| 未知形态回退 JSON；structured=None 显示「—」 | 通过（代码路径，未在真机造样本） |
| 清理后规则表计数 0 | 通过 |
