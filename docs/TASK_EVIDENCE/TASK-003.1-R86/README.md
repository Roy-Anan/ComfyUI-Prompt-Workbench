# TASK-003.1-R86 草稿「仅看收藏」勾选接入本地记忆

## 验收范围

- 对齐 R57 界面偏好本地记忆模式：草稿箱「仅看收藏」勾选状态写入
  `localStorage`（`workbench.favoredOnly`），刷新页面后恢复；纯前端，**后端零改动**。
- 切换 / 导入新工作流仍按 R83 复位勾选为未启用，并同步清除本地记忆；关键词检索词
  继续随草稿箱复位。`localStorage` 不可用时回落未启用，不抛错。
- 基线：`rules=0`、`history=0`、`tasks=0`、`model_identities=16`、草稿文件 0。

## 实现要点（`frontend/src/WorkflowWorkbench.tsx`）

- 模块级 `readStoredFavoredOnly()` 惰性初始化勾选状态；`persistFavoredOnly(value)`
  写本地存储，读写均 try/catch 兜底。
- 勾选 `onChange` 同时更新状态并写记忆；两处打开 / 导入工作流的复位路径在
  `setFavoredOnly(false)` 后补 `persistFavoredOnly(false)`，避免记忆与界面不一致。
- 未改后端契约、未新增端点、未改草稿数据结构；收藏标记本身仍由 R82 后端可逆字段承载。

## 真机与回归

- 后端 **241 passed, 1 warning**（见 `pytest-output.txt`；本切片未改后端，基线与 R85
  一致；StarletteDeprecationWarning 为遗留，与本项目无关）。
- 前端 `tsc -b && vite build` 绿（`frontend-build.txt`）；产物
  `index-DWmlVunC.js` 192.40 kB / gzip 60.95 kB，`index-BLYDrAOj.css` 9.78 kB /
  gzip 2.40 kB。
- 本机 127.0.0.1:17890（PID 21148）页面加载回归：工作流区空态与服务页正常渲染，
  控制台无报错；实例按身份回收，17890 无监听，pid/runtime 记录清除，库表复核回到基线。

## 边界与遗留

- 当前真机草稿数为 0，过滤行（含勾选框）仅在有草稿时渲染；勾选→刷新恢复→切流复位的
  完整闭环待有草稿阶段随批次真机终验。本地存储仅存布尔勾选，不存草稿内容。
- 草稿关键词检索词、历史其他筛选条件仍为会话态，未接入本地记忆；收藏分组 / 置顶 /
  按收藏导出留后续切片。
