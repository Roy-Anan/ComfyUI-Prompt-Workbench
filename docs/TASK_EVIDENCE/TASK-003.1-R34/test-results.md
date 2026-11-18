# R34 测试结果

## 后端 pytest

- 命令：`backend/  python -m pytest -q`
- 结果：**169 passed, 1 warning in 6.34s**
- 新增用例：CLIP/VAE 目录命中与未找到；已配置空目录判未找到（非未知）；未配置目录 `on_disk=None`；settings 外部目录空串白名单覆盖 clip/vae。
- 遗留 `StarletteDeprecationWarning` 与本切片无关。
- 原始输出：`pytest-output.txt`

## 前端构建 / 类型检查

- 命令：`frontend/  npm run build`（`tsc -b && vite build`）
- 结果：exit 0
- 产物：`index-DJeMbr87.js 165.64 kB │ gzip 53.30 kB`，CSS 8.09 kB
- 原始输出：`frontend-build.txt`

## 真机冒烟（浏览器 + API 只读验收）

| 检查点 | 结果 |
| --- | --- |
| Checkpoint 13 / LoRA 3 不回归 | 通过：`samples/catalog-payload.json` |
| CLIP 列展示（未列出占位） | 通过：`CLIP（0）ComfyUI 未列出 CLIP` |
| VAE 3 项未配置目录显示「目录未配置」 | 通过：`on_disk=None` |
| 存储区 CLIP/VAE 外部目录标签、可留空 | 通过：`screenshots/catalog-four-columns.png` |
| 未配置目录不把存在性误判为未找到 | 通过：全部 `None` |
| 清理后规则表计数 0 | 通过 |

目录命中 / 未找到分支由临时目录后端单测覆盖；真机 userdata 目录配置未改动。
