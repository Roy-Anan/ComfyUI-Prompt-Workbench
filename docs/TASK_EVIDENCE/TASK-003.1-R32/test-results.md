# R32 测试结果

## 后端 pytest

- 命令：`backend/  python -m pytest -q`
- 结果：**165 passed, 1 warning in 6.14s**
- 说明：本切片后端零改动；165 条既有回归全部通过。遗留 `StarletteDeprecationWarning` 与本切片无关。
- 原始输出：`pytest-output.txt`

## 前端构建 / 类型检查

- 命令：`frontend/  npm run build`（`tsc -b && vite build`）
- 结果：exit 0
- 产物：`index-Bgw4pSpK.js 165.10 kB │ gzip 53.22 kB`，CSS 8.09 kB
- 原始输出：`frontend-build.txt`

## 真机冒烟（浏览器只读验收）

| 检查点 | 结果 |
| --- | --- |
| 标题行文件名加粗（strong） | 通过 |
| 标题行无字面 `**` 星号 | 通过；`screenshots/title-bold.png` |
| 全前端 `.tsx` 无其他 markdown 残留 | 通过（检索确认） |
| 规则表计数 0 | 通过 |
