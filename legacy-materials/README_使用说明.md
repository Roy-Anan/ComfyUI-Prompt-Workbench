# ComfyUI Prompt Workbench — 使用说明（V2.0 正式版）

本机 Windows 上的 ComfyUI 提示词工作台。计划书七个阶段全部落地：规则包整合、Profile 精确匹配与自动注入、多轮对话与持久化、工作流导入与正负节点识别、一键提交 ComfyUI 出图并回显、显存自动管理、深色 UI / 运行状态 / 图片预览 / 错误提示 / 设置 / 日志 / 备份与最终打包。

- 版本：`2.0`
- 页面：<http://127.0.0.1:8199>
- 只监听 `127.0.0.1`，不对外网 / 局域网开放
- 最终包：`dist\ComfyUI_Prompt_Workbench_V2.0.zip`

## 交接与协作

- 人类接手先读 `交接说明.md`：当前状态、五分钟启动、文档阅读顺序、验收清单。
- AI 智能体接手先读 `AGENTS.md`：事实源优先级、目录归属、不可破坏约束、变更协议。
- 机器可读的版本、路径、命令、模块和阶段清单在 `PROJECT_MANIFEST.json`。
- 改完代码或文档后跑 `python tools\check_handover.py`，它会检查 manifest 与真实工程是否脱节。

## 启动

1. 先确认 **Ollama 桌面版 App** 在运行（任务栏有图标；没有就双击开始菜单里的 Ollama）。模型库在 `D:\AI\MODELS`，只有 App 认这个目录。
2. **要出图就先把 ComfyUI 跑起来**：打开绘世启动器启动秋叶整合包，确认 8188 端口可用（工作台顶部会显示“ComfyUI 在运行 0.30.2”）。只看提示词、不出图时不用开。
3. 双击 `启动工作台.bat`，或命令行：

```bat
"D:\AI\Qiuye\ComfyUI-aki-v3.2\python\python.exe" "D:\AI\ComfyUI_Prompt_Workbench\app\server.py"
```

4. `启动工作台.bat` 会在服务起来后自动打开默认浏览器；如果没弹出，手动打开 <http://127.0.0.1:8199>。

- 自动打开只由 `启动工作台.bat` 传入的 `--open-browser` 触发；直接运行 `app\server.py` 不弹浏览器，适合测试和后台启动。
- 本机没有系统级 Python，脚本固定用 ComfyUI 秋叶包自带的 Python 3.13.11（改路径就改 `启动工作台.bat` 的 `PYEXE`）。
- 出图前会**自动把 Ollama 模型从显存卸掉**（约 5.8 GB），出完图再自动装回来；不用手动点“卸载”。
- 顶部“显存”chip 显示当前已用 / 总容量与空闲；低于 `vram.min_free_mb` 时变红（Ollama 重新加载后本来就会红，属正常）。

## 页面怎么用

### 顶部

- 状态 chip：Ollama 版本、当前模型、ComfyUI 版本、显存读数；
- **运行条**：`空闲 / 对话中 / 出图中`、运行时长、对话次数、出图次数、最近事件、刷新按钮；
- `运行` / `日志` / `设置` 三个入口；
- 出错时顶部出现红色错误条，右下角同时弹 toast。

### 左栏

1. **会话**：历史对话列表（标题 / 更新时间 / 消息数 / Checkpoint）。点一条恢复整段对话；`新建` 开新对话；`×` 删除会弹确认，文件只移到 `history\conversations\_archive`。
2. **当前工作流**
   - 下拉列出 ComfyUI 自带工作流（只读）与工作台导入的（标 `·导入`）；
   - `导入` 按钮选本地 JSON：**UI Workflow（带 nodes/links）和 API Prompt（class_type 结构）都认**，存进 `workflows\`，不改 ComfyUI 原目录；同名自动加 `-2`、`-3`；
   - 详情区显示：格式、来源、Checkpoint、**正向节点 / 负向节点（按 KSampler 的 positive / negative 连线判定，不看节点标题和编号）**、LoRA 与强度、采样器 / 调度 / 步数 / CFG / seed、分辨率；
   - **人工映射**：正向 / 负向 / 采样节点三个下拉，选完点 `保存映射`，覆盖自动判定；清空即回到连线判定。导入的工作流可在这里删除（移到 `workflows\_archive`，ComfyUI 原目录不受影响）。
3. **模型 / Profile**：Checkpoint、架构 / 派系、匹配到的 profile；未登记标红并拒绝注入；LoRA 架构按文件头判定，不兼容会标红。
4. **查看注入给 Ollama 的内容**：展开可看到真正发过去的 system 全文与字符数（现在会写明“按连线判定”的节点号）。
5. **卸载 Ollama 模型**：`keep_alive=0` 从显存卸掉，服务不关。

### 右栏

1. 会话标题可改，回车即保存；`导出 MD` 下载整段对话。
2. 每条助手回复下：`出图`（用这条的 Positive / Negative 直接提交 ComfyUI）、`复制 Positive` / `复制 Negative` / `复制全文`。
3. `发送`（Ctrl+Enter）发新需求；`重新生成` 用同一条需求重跑。
4. **出图记录**（聊天区下方）：每张图显示状态、`generation_id`、耗时、`prompt_id`、seed / 步数 / CFG / 采样器 / 尺寸、正向提示词摘要；成功卡片多一行“显存：卸载 Ollama✓ · 释放 ComfyUI✓ · 恢复 Ollama✓ · 恢复对话✓ · 显存 199→6088 MB”。**点缩略图在页面内看大图**。失败的卡片有“重试”“查看日志”“复制错误”，成功的卡片可“再画一张（新种子）”“复制参数”。右上角“随机种子”勾选后每次换 seed，不勾就沿用工作流里的 seed。
5. 底部状态：注入字符数、profile、是否自动重试、token、是否落盘、提示词记录 ID。

## 阶段 7 新增功能

### 运行状态

运行条每 3 秒读一次 `GET /api/runtime`（页面切到后台时暂停）。它显示：

- 服务启动时间与运行时长；
- 当前活动任务（对话 / 出图，以及出图走到哪一步）；
- 对话、出图、错误计数；
- 最近一次成功或失败的结果；
- 最近错误原因。

### 图片预览

- 缩略图是按钮，点开 `lightbox`；
- 顶栏：`＋ / － / 适应` 缩放、`下载原图`、`关闭`；
- 底部：文件名、大小、seed、步数、CFG、采样器、调度器、尺寸、耗时、正向摘要；
- Escape 或点背景关闭。

### 错误提示

- 对话 / 出图 / 重试失败、接口 4xx/5xx、前端异常都会亮红色错误条；
- 错误条上的 `查看日志` 直接打开日志抽屉，并筛到 `error`；
- 右下 toast 显示操作结果，几秒自动消失；
- 前端异常通过 `POST /api/client-log` 上报，写进 `logs\workbench.log`。

### 设置页面

`设置` 打开五页：

| tab | 内容 |
| --- | --- |
| 应用 | 自动保存对话、出图后自动恢复 Ollama、删除前确认、深色主题 |
| 对话 | 历史消息条数（2–60）、系统提示词版本（精简版 / 全量版） |
| 系统信息 | 版本、Ollama / ComfyUI 地址与状态、数据目录、显存配置、历史统计、备份数量、日志路径、规则包体检 |
| 备份 | 备注、立即备份、备份列表、下载、删除 |
| 关于 | 版本、更新方式、部署说明、测试原则、已知边界入口 |

保存只认白名单键。非法值不会让整次保存失败，而是忽略该项并在底部黄色 `warnings` 写明；保存前把旧设置复制成 `settings\app_settings.bak.json`。

### 日志

- 文件：`logs\workbench.log`，JSON 行，UTF-8；
- 2 MB 滚动，保留 `workbench.log.1/.2/.3`；
- 页面右侧抽屉：路径、级别筛选（全部 / info / warn / error）、刷新、下载、条数；
- 记录对话、出图、显存、备份、设置、前端错误；**不写提示词正文和对话正文**；
- 重启后自动读回文件末尾，日志面板不会只剩“工作台启动”。

### 备份

- 页面“设置 → 备份”填备注，点“立即备份”；
- 备份 `history\`、`settings\`、`workflows\`、`config.json`；
- ZIP 内 `manifest.json`：版本、创建时间、备注、分类计数、每个文件的 `path / bytes / sha256`；
- 列表对每个 ZIP 做 CRC 校验，坏包标红；
- 删除只移到 `backups\_trash\`，可手动找回；
- **不含** `outputs\` 出图原图与 `logs\`，原因见“数据存在哪”。

## 出图怎么走

1. 点一条回复的 `出图` → 工作台把这条的 `【Positive Prompt】` / `【Negative Prompt】` 写进工作流解析出的正 / 负节点；
2. **显存准备**：读 Ollama 版本与 `/api/ps` → 把当前对话存一份 `history\contexts\` 快照 → 如果模型在显存里就 `keep_alive=0` 卸载并轮询确认 → 读 `nvidia-smi` 显存，空闲不够 `min_free_mb` 时最多等 `wait_free_seconds` → 读 ComfyUI 版本与队列；
3. 读 ComfyUI 的 `/object_info`（1444 个节点定义），按节点定义把 **UI Workflow** 转成 **API Prompt**：控件按 `input_order` 取，连线变成 `[来源节点, 槽位]`，跳过 `randomize` 这类前端占位值，Reroute 穿透，静音 / 旁路节点跳过，缺节点定义直接报错；
4. POST `/prompt` 提交，每秒轮询 `/history/{prompt_id}`，默认 300 秒超时；
5. 出图完成后从 `/view` 把图片下载到 `outputs\<generation_id>\01.png`，同时存一份 `prompt.json`（这次真正提交的 API Prompt）；
6. **收尾**：`POST /free`（`unload_models:true, free_memory:true`）释放 ComfyUI 模型与缓存 → 用空 prompt 的 `/api/generate` 把 Ollama 模型装回显存（`keep_alive` 取 `vram.reload_keep_alive`）→ 核对上下文快照与磁盘对话条数一致；
7. 结果写进 `history\generations\`（含 `vram` 九步时间线），页面“出图记录”按会话展示，刷新 / 重启都还在；
8. 提交时连不上 ComfyUI 会自动再试 1 次；执行失败 / 超时 / 没有图片，记录里留原因，卡片上可重试；显存准备失败会先回滚（把 Ollama 装回去）再返回错误；
9. **并发**：同一时刻只允许一张出图（服务端生成锁），第二张直接返回“上一张还在跑”。

**自动管理的开关**：`config.json → vram.auto_manage`，默认 `true`；单次请求可传 `"manage_vram": false` 跳过（例如 Ollama 已手动关掉、只想跑图）。设置页“出图后自动恢复 Ollama”会即时改 `vram.reload_ollama`。

**注意**：同一组提示词 + 同一个 seed 再提交，ComfyUI 会命中执行缓存，1–2 秒返回同一张图（`prompt_id` 是新的）；想真换一张勾“随机种子”或用卡片上的“再画一张（新种子）”。

## 显存自动管理

`config.json → vram`：

| 键 | 默认 | 作用 |
| --- | --- | --- |
| `auto_manage` | `true` | 出图默认自动走完整条链路 |
| `min_free_mb` | `4000` | 出图前希望空闲的显存；不够就等 |
| `wait_free_seconds` | `40` | 等显存释放的上限 |
| `poll_interval` | `1.0` | 轮询间隔（秒） |
| `free_comfy_after` | `true` | 出图后是否 `POST /free` |
| `free_wait_seconds` | `20` | 等 `/free` 后显存下降的上限 |
| `unload_wait_seconds` | `20` | 等 `/api/ps` 变空的上限 |
| `reload_ollama` | `true` | 无模型驻留时也预加载（保证能接着聊）；设置页可改 |
| `reload_wait_seconds` | `15` | 预加载后确认 `/api/ps` 的上限 |
| `reload_keep_alive` | `30m` | 恢复时给 Ollama 的 keep_alive |
| `strict_vram` | `false` | `true` 时空闲不够直接失败；默认只警告并继续尝试 |

每次出图的 `vram.steps` 固定九步：`ollama_detect` → `context_snapshot` → `ollama_unload` → `gpu_check` → `comfy_check` → `comfy_free` → `ollama_reload` → `context_restore` → `gpu_after`，每步带 `ok / detail / 时间 / 显存读数`。

**实测数值（RTX 4060 Laptop 8GB）**：Ollama 模型 `size_vram` 5,783 MB；卸载后空闲 7,758 MB；出图后 ComfyUI 占用 4,686 MB，`/free` 后降到 206 MB；恢复 Ollama 后已用 6,095 MB。Ollama 与 ComfyUI 同时驻留必爆显存，所以只能串行。

## 正负节点怎么判定

从采样节点的 `positive` / `negative` 输入出发，顺着连线往上游回溯：

- 碰到 `CLIPTextEncode`（或同类文本节点）就收下它的文本；
- 中间有 `ConditioningCombine` 之类节点会继续往上追，多个文本节点会一起收；
- 节点标题写反、编号顺序反了都不影响结论；
- 找不到采样节点、或连线上没有文本节点时，**明确标“未判定”并给出提示**，不用编号猜，也不默默给个默认值；
- 需要时用人工映射覆盖。

UI 格式（`nodes` + `links`）与 API 格式（`[来源节点, 槽位]`）走同一套判定逻辑。

## 数据存在哪

```text
history\
  conversations\<conversation_id>.json     一段对话一个文件
  prompts\<prompt_id>.json                 每次应答抽出的 Positive / Negative
  generations\<generation_id>.json         每次出图：参数、prompt_id、图片、状态、vram 步骤
  contexts\<conversation_id>-<时间>.json   出图前的对话上下文快照（证明可恢复）
  history_index.json                       列表索引
  conversations\_archive\                  删除的对话
settings\
  app_settings.json                        自动保存、上下文条数、提示词版本、恢复开关
  app_settings.bak.json                    保存前的上一版
outputs\
  <generation_id>\01.png                   出图原图（工作台自己的副本）
  <generation_id>\prompt.json              这次真正提交的 API Prompt
workflows\
  <导入的工作流>.json                      工作台自己的副本（原目录不动）
  mappings\<名字>.mapping.json             人工节点映射
  workflows_index.json                     导入记录（内部索引，不作为工作流出现在下拉）
  _archive\                                删除的工作流
logs\
  workbench.log                            运行日志；滚动 workbench.log.1/.2/.3
  测试结果_阶段7.txt / 冒烟结果_阶段7.txt   测试证据
  UI截图_阶段7_*.png                       浏览器实测截图
backups\
  backup-YYYYMMDD-HHMMSS.zip               备份（含 manifest.json）
  _trash\                                  删除的备份（只移动，不抹除）
rules_source\
  模型说明.xlsx                            13 个底模对照、SHA256、分级与标签字典（人工参考）
```

- 对话、提示词、出图记录、设置、工作流映射全部落盘；浏览器刷新、关页面、关工作台、重启 Windows 都不丢。
- 出图图片存两份：ComfyUI 自己的 `output\` 一份，工作台 `outputs\` 一份；清 ComfyUI 输出目录不影响工作台回显。
- 写入用「临时文件 + `os.replace`」；设置文件读坏会改名留证再回默认值。
- 备份不含 `outputs\` 和 `logs\`：出图原图大、ComfyUI 原目录还有一份；日志是排错材料。需要连图备份时手动复制 `outputs\`。
- **程序包不含** `history\`、`settings\`、`outputs\`、`backups\`（用户数据与出图结果）；`workflows\` 里只带空目录结构；`logs\` 保留测试证据。

## 接口

| 接口 | 说明 |
| --- | --- |
| `GET /api/health` | 状态、版本、历史统计 |
| `GET /api/status` | Ollama / 模型 / ComfyUI / 显存 / 最近一次显存会话 |
| `GET /api/runtime` | 运行状态快照 + 最近日志 + 最近显存摘要 |
| `GET /api/logs?limit=&level=` | 日志条目 + 日志文件信息 |
| `GET /api/logs/download` | 下载日志文本 |
| `GET /api/backups` | 备份列表 + 数量 / 占用 |
| `POST /api/backups` | 立即备份（`{note}`） |
| `GET /api/backups/<name>/download` | 下载备份 ZIP |
| `POST /api/backups/<name>/delete` | 删除备份（移到 `_trash`） |
| `POST /api/client-log` | 前端错误上报（`{level,message,detail,url}`） |
| `GET /api/vram` | 显存配置、当前 GPU 读数、Ollama 驻留模型、最近一次链路 |
| `GET /api/models` | 13 个登记模型 |
| `GET /api/lookup?name=` | Profile 精确匹配 |
| `GET /api/integrity` | 映射 / profile / 索引 / 磁盘 checkpoint 四方体检 |
| `GET /api/workflows` | 工作流列表（ComfyUI + 工作台，含格式 / 正负节点） |
| `POST /api/workflows/import` | 导入 UI / API JSON（`{name, content}`） |
| `POST /api/workflows/mapping` | 人工映射（`{name, positive_node, negative_node, sampler_node}`） |
| `POST /api/workflows/delete` | 删除工作台导入的工作流（归档） |
| `GET /api/workflow?name=` | 解析详情（正负节点、LoRA、采样、分辨率） |
| `GET /api/context?workflow=` | 注入预览（完整 system） |
| `GET /api/conversations` | 对话列表 |
| `POST /api/conversations` | 新建对话 |
| `GET /api/conversations/<id>` | 整段对话 + 提示词记录 |
| `POST /api/conversations/<id>/rename` | 改标题 |
| `POST /api/conversations/<id>/delete` | 删除（归档） |
| `GET /api/conversations/<id>/export` | 导出 Markdown |
| `GET /api/prompts?conversation_id=` | 提示词记录 |
| `GET` / `POST /api/settings` | 读写设置（写前备份、白名单键；响应含 `warnings` / `system`） |
| `POST /api/chat` | 对话（`{conversation_id, message, workflow}` 或 `{conversation_id, regenerate:true}`） |
| `POST /api/unload` | 卸载 Ollama 模型 |
| `POST /api/generate` | 提交出图（`{conversation_id, workflow, positive, negative, seed?, steps?, cfg?, width?, height?, batch?, manage_vram?}`；`seed:"randomize"` 换随机种子；`manage_vram:false` 跳过显存自动管理） |
| `GET /api/generations?conversation_id=` | 出图记录列表 |
| `GET /api/generations/<gid>` | 单条出图记录 |
| `GET /api/generations/<gid>/image/<n>` | 图片回显（读工作台 `outputs\` 的副本） |
| `POST /api/generations/<gid>/retry` | 按记录参数重试/再画（`{randomize:true}` 换种子） |

所有工作流名、备份名都做 basename 校验，带 `/`、`\`、`..` 的输入直接拒绝。

## 注入结构

1. `rules\系统提示词_Ollama精简版.txt` 全文（设置里可切全量版）；
2. `【当前模型】` + 架构 / 派系 / 画风 + 匹配依据；
3. 该模型 profile 原文，一字不改；
4. `【当前工作流上下文】`：Checkpoint、**正向 / 负向节点（按连线判定）**、LoRA、采样参数、分辨率、提示与警告；
5. `【工作台附加约束】` + `【要求】`。

未登记的 Checkpoint 直接拒绝，不编 profile。

## 对话参数与防跑飞

- `config.json → ollama.options`：temperature 0.35、top_p 0.85、top_k 20、num_ctx 8192、repeat_penalty 1.3、num_predict 1400。
- 失控检测（`app/output_guard.py`）：> 5200 字符、逗号 > 180、同一三词短语连续重复 > 3 次判失控。
- 命中后用更低温度重试，**最多再试两次（temperature 0.2 / 0.1，num_predict 900 / 700，repeat_penalty 1.4 / 1.5）**，取“未失控优先、其次更短”的结果；界面会写自动重试次数。
- 仍可能遇到模型偶发跑飞（本机 8B 量级模型的老问题），这时该轮可能抽不出六段结构，提示词记录会缺一条，日志和消息里都留痕。

## 测试

```bat
cd /d D:\AI\ComfyUI_Prompt_Workbench
"D:\AI\Qiuye\ComfyUI-aki-v3.2\python\python.exe" -m unittest discover -s tests -v
"D:\AI\Qiuye\ComfyUI-aki-v3.2\python\python.exe" -u tests\smoke_server.py
"D:\AI\Qiuye\ComfyUI-aki-v3.2\python\python.exe" tools\check_ui.py
"D:\AI\Qiuye\ComfyUI-aki-v3.2\python\python.exe" tools\check_handover.py
```

- 单元测试 **129/129**（阶段 1–6 112 + 阶段 7 的 17）。
- 交接结构自检：检查 manifest、文档、模块、测试、阶段证据和最终 ZIP，应输出 `PASS`。
- 冒烟 **128/128**：真起服务、真导入 UI/API 工作流、真人工映射、真两轮对话、**真出图 62.0 秒（图片 1,432,359 字节）**、**真卸载 Ollama（5,783 MB）→ 出图 → `/free` 4,686→206 MB → 重新加载 Ollama → 第 3 轮对话**、真失败计数 / 真错误日志、真重启、真备份 / 下载 / 删除、真删除对话只归档。
- 浏览器 UI 自检 **22/22**（`tools\ui_probe.py`，需要 Chrome + `websocket-client`）。
- 证据：`logs\测试结果_阶段7.txt`、`logs\冒烟结果_阶段7.txt`、`logs\阶段7_UI自检结果.json`、`logs\UI截图_阶段7_*.png`。
- 注意：`smoke_server.py` 硬编码 8199，跑之前先把正在运行的工作台停掉，跑完再启动。

## 匹配规则（不要放松）

- 只认 `rules\模型数据库.txt` 里登记的**完整 checkpoint 文件名**；
- 允许子目录前缀与大小写差异，但标记 `case-insensitive`；
- 不做关键词 / 前缀 / 相似度匹配，未登记一律提示建档。

## 加新底模

改模型或核对参数前，先查 `rules_source\模型说明.xlsx`：里面有 13 个底模的架构、派系、画风标签、SHA256、推荐采样参数、分级与标签字典，可直接当人工核对表；工作台运行时仍以 `rules\模型数据库.txt` 和 `profiles\` 为准。

1. 复制 `rules_source\ComfyUI_Prompt_Master_V1\TEMPLATES\NEW_MODEL_PROFILE_TEMPLATE.txt`；
2. 填好存为 `profiles\你的模型名.txt`；
3. `rules\模型数据库.txt` 加一行 `完整文件名.safetensors = MODEL_PROFILES/你的模型名.txt`；
4. `rules\模型索引_Ollama.txt` 补一行；
5. 跑测试，确认 `integrity.ok == true`。

## 规则口径（不得改写）

`[已核实]` / `[镜像核实]` / `[作者推荐]` / `[作者示例]` / `[作者指南]` / `[已实测]` / `[起始测试值]` / `[待核实]` / `[未给出]` 原样保留。

## 与 Ollama 的关系

- 模型库在 `D:\AI\MODELS`，由 Ollama 桌面版 App 提供；`ollama list` 能看到 `qwen3:latest` 与 `comfyui-prompt:v1`。
- 不要另起 `ollama serve`：默认模型库是空的。
- 环境里的 `OLLAMA_HOST=10.212.135.209:11434` 不吃；工作台固定 `127.0.0.1`。
- 8GB 显存：Ollama 与 ComfyUI 不能同时挂；出图时工作台会自动卸载 / 恢复。

## V2.0 的边界

- 主题只做深色；设置里选浅色会被强制回 `dark`。
- 备份不含 `outputs\` 出图原图与 `logs\`。
- 日志面板显示最近 600 条；更早看文件或滚动文件。
- `confirm_delete` 是页面二次确认；直接调删除 API 不弹确认（本机单人工具）。
- 出图 400 校验失败也计入 `errors`，运行条会显示“出过错”。
- 端到端只在 RTX 4060 Laptop 8GB + ComfyUI 0.30.2 + Ollama 0.40.15 实测；其他显卡 / 版本未验证。
- 详细实现与测试记录见 `阶段7_实施记录.md`；部署与升级见 `部署步骤_Windows.md`；变更清单见 `更新说明.md`。
