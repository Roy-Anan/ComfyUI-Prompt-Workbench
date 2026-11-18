# TASK-003.1-R66 版本快照恢复（恢复旧版本产生新版本）

## 验收范围

- M5 验收口径「恢复旧版本产生新版本」：在既有版本快照只读列表（R54）之上，补一条恢复链路——
  取指定历史快照白名单 Prompt 文本，走既有受保护的 `write_prompts` 写回当前工作副本；
  `write_prompts` 写入前会先把当前工作副本存为一个新的版本快照，因此恢复旧版本本身会产生一个新版本。
- 基线：health `0.1.0-dev.5` / Python 3.13.18；`rules=0`，`profiles=13`；
  Ollama `127.0.0.1:11434`、ComfyUI `127.0.0.1:8188` 在线。

## 后端实现要点（`backend/workflow_service.py` / `workflow_api.py`）

- `WorkflowStore.restore_version(workflow_id, stamp)`：
  - `_folder(id)` UUID 校验 + resolve 防越界；目录须存在；manifest 校验 `format==api`、`confirmed`。
  - 快照标识经 `Path(stamp).name` 归一化，须与原串一致且不含 `..`；快照路径 resolve 后必须落在
    `versions/` 目录内（防路径越界）；快照须为文件。
  - 读取快照后按 manifest 白名单逐节点提取 `role=positive/negative` 的首个字符串 `inputs.text`；
    两类均为空时报 `WorkflowError`「该版本快照没有可恢复的 Prompt 文本」。
  - 最终 `return self.write_prompts(workflow_id, positive_text, negative_text)`，复用既有白名单
    写入与前置/后置完整性校验，不另立写入模型。
- 端点：`POST /api/workflows/{workflow_id}/versions/{stamp}/restore`（无 body）；异常走既有
  `_raise_api_error`；返回结构与 `write_prompts` 一致 `{ok, changes, working_fingerprint, workflow}`。
- 测试：服务层 2 例（写回快照文本并新增一条新版本快照；缺失快照与 `../escape` 越界拒绝）；
  端点层 2 例（写回并新增快照；未知工作流 404）。

## 前端实现要点（`frontend/src/WorkflowWorkbench.tsx`）

- 新增 `restoringStamp`、`confirmStamp` 状态；`restoreVersion(stamp)` 调恢复端点，成功后
  `setDetail` 并同步正/负向文本框，重载版本列表，消息「已恢复所选版本；当前内容已另存为一个新的
  历史版本快照。」
- 版本条目按钮为两步内联确认：首点进入确认态（「再次点击确认恢复」+「取消」），二次点击才提交；
  不使用原生 `window.confirm`（同步弹窗会阻塞自动化主线程）；恢复中 / 繁忙禁用。
- 面板标题由「历史版本（只读）」改为「历史版本」；切换工作流时清空确认态。

## 真机闭环（本机 127.0.0.1:17890，PID 23168）

- 后端直连：导入最小 API 样本 → 确认节点 → 写 v1、写 v2；版本 2 条（v1、old）。
  恢复 v1 快照后：当前工作副本回退为 `v1 positive` / `v1 negative`；版本由 2 变 3，
  最新快照为恢复前的 v2 工作副本。缺失快照返回 400「指定的版本快照不存在」；越界标识被拒。
- 浏览器：打开临时副本，版本列表两条快照各带「恢复此版本」；首点进入确认态，二次点击确认恢复；
  消息「已恢复所选版本；当前内容已另存为一个新的历史版本快照。」；编辑框当前值回退 v1；
  版本列表三条（v2 新快照、v1、old）。
- 截图：`acceptance-r66-versions.png`（版本列表与恢复按钮）、`acceptance-r66-confirm.png`
  （两步确认态）、`acceptance-r66-restored.png`（恢复后三条版本，最新为 v2 新快照）。

## 收尾

- 冒烟临时副本目录已删除，`workflows` 回到基线 22 个；`rules=0`、`profiles=13`；
  Ollama、ComfyUI 外部进程未触碰。
- stopper 按结构化身份回收实例（PID 23168，含子进程），端口 17890 关闭。

## 回归

- 后端：**229 passed, 1 warning**（`pytest-output.txt`；StarletteDeprecationWarning 为遗留，
  与本项目无关）。较 R64/R65 基线 225 增加 4 例（服务层 2 + 端点层 2）。
- 前端：`tsc -b && vite build` 绿（`frontend-build.txt`）；产物
  `index-C6s1S_OZ.js` 180.85 kB / gzip 57.71 kB，`index-X0JFovQF.css` 9.42 kB / gzip 2.33 kB。

## 边界与遗留

- 同 role 多节点沿用既有 `write_prompts` 聚合口径；恢复提取按 role 取首个节点文本，不做多节点
  逐字段合并。
- 未实现：多草稿 / 草稿箱、版本备注、版本差异对照、标签 / 收藏 / 搜索 / 回收站（M5 既有 backlog）。
- 未改动白名单写入、CSRF、回环绑定、unknown 不臆测等安全口径。
