# 安全加固审查报告 — TASK-002.3.1

## 1. 监听地址限制

- 实现：`main.is_loopback_host()` 与启动器前置校验；接受 `127.0.0.1`、`localhost`、`::1` 及解析后全为回环的名字；拒绝 `0.0.0.0`、局域网与公网 IP。
- 实测：真机仅 `127.0.0.1:8000` 处于 LISTENING（PID 7124），未绑定 `0.0.0.0`。
- 测试：`test_loopback_host_accepts_local_names`、`test_loopback_host_rejects_public_and_lan`；启动器 `test_launcher_loopback_accepts_local` / `test_launcher_loopback_rejects_public_lan`。

## 2. PID 身份核验（防复用误杀）

- 实现：停止器经 CIM 读取 `ExecutablePath`、`CommandLine`、`CreationDate`；校验可执行路径为项目 `.venv\Scripts\python.exe`，命令行含 `uvicorn` 与 `main:app` 且指向项目后端。
- fail-closed：关键属性缺失或不匹配时不终止，输出警告保留现场；不按 Python / uvicorn 名称批量结束进程。
- 实测：首次健康识别失败残留的工作台进程树（父 16036 / 子 27532）被停止器正确识别并回收，端口归零；未影响其他 Python 服务。
- 测试：`test_stopper_rejects_identity_mismatch`（路径不匹配 / 身份缺失均拒绝）、`test_stopper_matches_workbench_process`。

## 3. 进程树停止

- 实现：`descendant_pids()` 递归收集整棵子进程树后一并回收。
- 边界：只结束本工作台进程树；Ollama、ComfyUI 与其他 Python 服务不在结束范围内。

## 4. 静态路径前缀碰撞与穿越

- 实现：`_resolve_within_dist()` 先 `unquote` 解码 URL 编码，再 `Path.resolve()` 后用 `relative_to(dist_root)` 做真实路径包含判断；拒绝 `../`、`%2e%2e%2f`、`..%2f` 与相邻目录前缀碰撞（`dist-other`）。
- 测试：
  - `test_static_path_traversal_is_rejected`
  - `test_static_url_encoded_traversal_is_rejected`
  - `test_static_adjacent_prefix_collision_is_rejected`
  - `test_static_normal_asset_resolves_inside_dist`（正常资源仍可访问）

## 5. 健康检查身份核验

- 问题：`/api/health` 原被认证中间件拦截返回 401，启动器拿不到含应用标识的响应体，无法区分本工作台实例与端口上的其他服务。
- 处理：中间件对 `/api/health` 提前放行，作为未认证身份探测；响应体携带 `app` / `app_id`、`version`、`python`、`platform`，不含用户数据。启动器 `health_identifies_workbench()` 要求 `app` 或 `app_id` 等于 `ComfyUI-Prompt-Workbench` 才判定就绪。
- 实测：无会话 `GET /api/health` 返回 200 与应用标识；`/api/services/status`、`/api/settings` 无会话仍返回 401。
- 测试：`test_health_is_unauthenticated_identity_probe`；启动器 `test_launcher_health_requires_identity`（空 200 不算识别，正确标识才算识别）。

## 6. 保留的既有安全约束

- 会话票据仅存后端进程内存；`/api/bootstrap` 同源签发 HttpOnly Cookie 与 CSRF Cookie；状态变更需 `X-Workbench-CSRF` 头；Origin 白名单校验；引导令牌仅经环境变量传递，不入前端产物。
- 本次未关闭 API 认证，未默认开放局域网 / 公网，未上传 token / 密码 / 隐私 / 模型权重 / 原始图片。
