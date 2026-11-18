# TASK-003.1-R85 服务卡片只读展示 ComfyUI 显存与队列在况

## 验收范围

- 在「服务与设置」页 ComfyUI 状态卡片，只读对接既有后端端点
  `GET /api/comfyui/status`（R39 设备/显存快照）与 `GET /api/comfyui/queue`（R40 队列/历史投影），
  展示 ComfyUI 版本、逐设备显存空闲/总量、队列运行中/待执行计数。
- **后端零改动**；纯前端只读 GET，不做显存阈值判断、不控制 ComfyUI/Ollama 进程、不提交/取消/调整队列。
- 离线、超时或字段缺失时保守显示「—」「显存信息未知」「队列状态未知」，不臆造数值。
- 基线：`rules=0`、`history=0`、`tasks=0`、`model_identities=16`、草稿文件 0。

## 实现要点（`frontend/src/App.tsx`、`frontend/src/styles.css`）

- 新增类型 `ComfyDevice` / `ComfyStatus` / `ComfyQueue`，与后端既有返回结构对齐；
  模块级 `formatGiB(bytes)` 将字节换算为 GiB（`/1024**3`，保留 1 位），`null`/NaN/负数回退 `—`。
- 新增会话态 `comfyStatus`、`comfyQueue`；`refresh()` 在主链路 `Promise.all` 之后对两个端点
  各自独立 `.then(set…).catch(() => setNull)`，取不到置空，不拖垮主面板连接状态。
- ComfyUI 卡片：有版本号时显示「版本 x」；在线且设备非空时逐设备渲染
  `设备名：显存 空闲 / 总量`；在线但无设备显示「显存信息未知」；队列在线显示
  `队列：运行中 N · 待执行 M`，否则「队列状态未知」。
- `.status-card small` 补 `display: block; margin-top: 4px;`，使 URL/版本/设备/显存/队列
  各占一行（既有卡片仅单个 small，此前未暴露连排问题）。

## 真机闭环（本机 127.0.0.1:17890，PID 17596）

- 首载时外部服务在线，卡片经 DOM 读到：ComfyUI 在线、版本 `0.30.2`；设备
  `cuda:0 NVIDIA GeForce RTX 4060 Laptop GPU : cudaMallocAsync`，显存
  **6.9 GB 空闲 / 8.0 GB**（后端原始 `vram_free=7451181056`、`vram_total=8585216000`，
  换算与前端显示一致）；队列 **运行中 0 · 待执行 0**；Ollama 在线 `127.0.0.1:11434`。
- 复测时 ComfyUI（8188）与 Ollama（11434）已退出，直连探测返回 `WinError 10061` 拒绝连接；
  后端保守回报离线，卡片显示「未连接」「队列状态未知」，未臆造显存或队列数值（fail-closed）。
  `screenshots/r85-status-cards.png` 为该离线态：块级换行已生效，URL 与队列行分行显示。
- 补档轮次外部服务经命令行临时拉起用于验收：`screenshots/r85-status-cards-online.png`
  为在线合并截图——工作台本地服务已连接（Python 3.13.18）、Ollama 在线 11434、
  ComfyUI 在线 8188，版本 `0.30.2`，RTX 4060 Laptop GPU 显存 **6.9 GB 空闲 / 8.0 GB**，
  队列 **运行中 0 · 待执行 0**；URL/版本/设备/显存/队列块级分行排版正确。
- 本轮全程未提交 ComfyUI 任务、未写入规则/历史/任务记录；结束后库表复核回到基线。

## 回归

- 后端：**241 passed, 1 warning**（见 `pytest-output.txt`；本切片未改后端，基线与 R84
  一致；StarletteDeprecationWarning 为遗留，与本项目无关）。
- 前端：`tsc -b && vite build` 绿（`frontend-build.txt`）；产物
  `index-D5CHVVs6.js` 192.18 kB / gzip 60.91 kB，`index-BLYDrAOj.css` 9.78 kB /
  gzip 2.40 kB。

## 边界与遗留

- 显存空闲阈值（出图前必须空闲多少 GB）口径未拍板，本切片只做只读展示，不做放行/拒绝判断；
  阈值闸门待后续确认后再实现。
- 工作台不内置启停 ComfyUI/Ollama 进程；补档轮次的外部服务为命令行临时拉起、验收后回收，
  产品代码口径不变。在线新样式（块级排版 + 显存/队列数值）合并截图已补拍归档。
- 队列暂停/恢复、待执行顺序调整、WebSocket 进度与断线恢复不在本切片范围。
