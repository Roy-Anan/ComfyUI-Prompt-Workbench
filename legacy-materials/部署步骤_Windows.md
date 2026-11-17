# ComfyUI Prompt Workbench V2.0 — Windows 部署步骤

适用：Windows 10/11 x64、NVIDIA 显卡、秋叶 ComfyUI 整合包、Ollama 桌面版。
本机验证环境：RTX 4060 Laptop 8GB、ComfyUI 0.30.2、Ollama 0.40.15、Python 3.13.11（秋叶包自带）。

---

## 一、先确认三件事

1. **Ollama 桌面版在运行**
   - 任务栏有 Ollama 图标；没有就打开开始菜单里的 Ollama。
   - 浏览器访问 <http://127.0.0.1:11434/api/tags> 能返回 JSON。
   - 模型库在 `D:\AI\MODELS`（Ollama App 的设置里确认），`comfyui-prompt:v1` 在列表里。
   - 不要另起 `ollama serve`：默认模型库是空的，会看不到模型。

2. **ComfyUI 能出图（只在要出图时需要）**
   - 用绘世启动器打开秋叶整合包；
   - 浏览器访问 <http://127.0.0.1:8188> 能打开 ComfyUI；
   - 工作台顶部状态 chip 显示“ComfyUI 在运行 0.30.2”。

3. **Python 路径**
   - 本机没有系统级 Python，工作台固定用秋叶包自带的：
     `D:\AI\Qiuye\ComfyUI-aki-v3.2\python\python.exe`
   - 如果你的秋叶包在别的盘 / 别的目录，改 `启动工作台.bat` 里的 `PYEXE`。

---

## 二、全新安装

1. 把 `ComfyUI_Prompt_Workbench_V2.0.zip` 解压到 `D:\AI\ComfyUI_Prompt_Workbench`。
   - 解压后根目录应能看到 `app\`、`web\`、`rules\`、`profiles\`、`tests\`、`tools\`、`config.json`、`启动工作台.bat`。
   - 不要解压到 `C:\Program Files` 或需要管理员权限的目录；工作台要写 `history\`、`settings\`、`outputs\`、`logs\`、`backups\`。

2. 检查 `config.json`：
   - `app.port` 默认 `8199`；
   - `ollama.base_url` 默认 `http://127.0.0.1:11434`；
   - `comfyui.base_url` 默认 `http://127.0.0.1:8188`；
   - `vram.auto_manage` 默认 `true`；8GB 显存不要改 `batch`。

3. 双击 `启动工作台.bat`。
   - 窗口里出现 `打开：http://127.0.0.1:8199` 和 `退出：Ctrl+C` 后，浏览器打开 <http://127.0.0.1:8199>。
   - 只监听 `127.0.0.1`，不对外网 / 局域网开放，不需要改防火墙。

4. 页面顶部应看到：
   - 左侧 `Ollama 在运行 0.40.15`、ComfyUI 状态、显存 chip；
   - 中间运行条“空闲 · 对话 0 · 出图 0”；
   - 右上 `运行 / 日志 / 设置` 三个按钮。

5. 冒烟自检（可选，第一次部署建议做）：

```bat
cd /d D:\AI\ComfyUI_Prompt_Workbench
"D:\AI\Qiuye\ComfyUI-aki-v3.2\python\python.exe" tools\check_ui.py
```

看到“结论：通过”即可。`tools\ui_probe.py` 是开发机的浏览器自检，需要 `websocket-client`，普通使用不必跑。

---

## 三、从阶段 6 升级到 V2.0

程序包**不含用户数据**：`history\`、`settings\`、`outputs\`、`backups\` 都不在 ZIP 里。升级时按下面做，不会丢会话和出图。

1. 停掉正在运行的工作台（关掉 `启动工作台.bat` 窗口，或任务管理器结束那个 `python.exe`）。
2. 在页面“设置 → 备份”点“立即备份”，记下备份文件名；或直接复制整个 `backups\` 目录到别处。
3. 把新 ZIP 解压到一个临时目录，例如 `D:\AI\ComfyUI_Prompt_Workbench_new`。
4. 把临时目录里的**程序文件**覆盖到 `D:\AI\ComfyUI_Prompt_Workbench`：
   - 覆盖 `app\`、`web\`、`rules\`、`profiles\`、`tests\`、`tools\`、`启动工作台.bat`、文档；
   - **不要**覆盖 / 删除 `history\`、`settings\`、`outputs\`、`workflows\`、`backups\`、`logs\`。
5. `config.json`：如果本机改过端口 / 地址，先备份旧文件，再把新文件的 `app.port`、`ollama.base_url`、`comfyui.base_url` 改回旧值；没改过就直接用包里的默认。
6. 重新双击 `启动工作台.bat`，打开页面确认：
   - 会话列表还在；
   - 出图记录和缩略图还在；
   - 设置里“历史消息条数”仍是原来的值；
   - 版本显示 `V2.0 · 正式版`。
7. 需要回到旧版：停服务，把旧程序文件覆盖回来；数据目录不动。

---

## 四、日常启动顺序

推荐顺序：

1. Ollama 桌面版（聊提示词必须）；
2. 秋叶 ComfyUI（要出图才开）；
3. `启动工作台.bat`；
4. 浏览器 <http://127.0.0.1:8199>。

8GB 显存下 Ollama 与 ComfyUI 不能同时驻留。工作台出图时会自动：

```text
读显存 → 卸载 Ollama（keep_alive=0）→ 提交 ComfyUI → 下载图片
→ POST /free 释放 ComfyUI → 重新加载 Ollama → 恢复对话
```

设置里的“出图后自动恢复 Ollama”关掉后，出图结束不会预加载 Ollama，下一次聊天会慢一些。

---

## 五、备份与恢复

### 5.1 备份

页面“设置 → 备份”：

- 备注可留空；
- 点“立即备份”，生成 `backups\backup-YYYYMMDD-HHMMSS.zip`；
- 列表里可下载 / 删除；删除只是移到 `backups\_trash\`，不会立刻抹掉。

命令行等价：

```bat
"D:\AI\Qiuye\ComfyUI-aki-v3.2\python\python.exe" -c "import sys;sys.path.insert(0,r'D:\AI\ComfyUI_Prompt_Workbench');from app.backup import BackupManager;b=BackupManager(r'D:\AI\ComfyUI_Prompt_Workbench');print(b.create('手工备份'))"
```

备份包含：`history\`、`settings\`、`workflows\`、`config.json`。
备份不含：`outputs\`（出图原图）、`logs\`（排错日志）、`backups\` 自身。

### 5.2 恢复

1. 停掉工作台；
2. 解压备份 ZIP 到临时目录；
3. 确认 `manifest.json` 里的 `file_count` 与解压文件数一致；
4. 把 `history\`、`settings\`、`workflows\`、`config.json` 覆盖回工作台根目录；
5. 重新启动，页面确认会话、设置、工作流都在。

出图原图如果也要恢复，手动把 `outputs\` 复制回去；备份没有包含它。

---

## 六、常见故障

| 现象 | 处理 |
| --- | --- |
| 页面打不开 | 看 `启动工作台.bat` 窗口有没有报错；确认 8199 没被别的程序占用：`netstat -ano | findstr :8199` |
| 顶部 Ollama 红 | 打开 Ollama 桌面版；访问 `http://127.0.0.1:11434/api/tags`；确认模型名是 `comfyui-prompt:v1` |
| ComfyUI 红 / 出图失败 | 秋叶启动器是否在跑；访问 `http://127.0.0.1:8188`；看 `logs\workbench.log` 最近错误 |
| 出图报显存不足 | 8GB 下确认 `vram.auto_manage=true`、`batch=1`；关掉其他吃显存的程序；不要同时开 Ollama 和 ComfyUI 大模型 |
| 出图很快返回同一张图 | 同提示词 + 同 seed 命中 ComfyUI 执行缓存；勾“随机种子”或点“再画一张（新种子）” |
| 设置保存后没生效 | 看设置页底部黄色 warning；被收窄 / 忽略的键会写明原因 |
| 日志中文变问号 | 用 Python / 浏览器请求；PowerShell 5.1 的 `Invoke-WebRequest` 可能按错误编码发中文，属于客户端问题 |
| 备份下载后打不开 | 在“备份”列表看该项是否 `ok`；CRC 失败说明 ZIP 损坏，换一个备份或看 `_trash` |
| 想彻底重置 | 停服务，把 `history\`、`settings\`、`outputs\`、`backups\` 改名留证，工作台会按默认重建；不要直接删，先备份 |

---

## 七、目录说明

```text
D:\AI\ComfyUI_Prompt_Workbench\
  app\            服务端（server.py、日志、运行态、备份、显存、ComfyUI 客户端）
  web\            前端（index.html、style.css、app.js）
  rules\          规则包（模型数据库、系统提示词、模型索引）
  profiles\       13 个模型 profile
  rules_source\   规则包原始资料
  tests\          单元测试与冒烟测试
  tools\          打包、校验、UI 自检、交接自检、清理脚本
  AGENTS.md       AI / 多智能体协作入口
  交接说明.md      人类交接入口、状态、验收清单
  PROJECT_MANIFEST.json  机器可读的版本、路径、命令、模块、阶段清单
  config.json     端口 / 服务地址 / 显存参数
  logs\           workbench.log、测试记录、UI 截图
  history\        会话、提示词、出图记录、上下文快照（用户数据）
  settings\       应用设置与备份（用户数据）
  outputs\        出图原图（用户数据）
  workflows\      导入的工作流与映射（用户数据）
  backups\        备份 ZIP 与 _trash（用户数据）
  dist\           发布 ZIP
```

---

## 八、卸载

1. 停掉工作台；
2. 需要保留会话 / 出图 / 设置，先把 `history\`、`settings\`、`outputs\`、`workflows\`、`backups\` 复制到别处；
3. 删除 `D:\AI\ComfyUI_Prompt_Workbench` 整个目录；
4. 工作台不写注册表、不装服务、不改系统环境变量，删目录即可。
