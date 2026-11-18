# TASK-003.1-R64/R65 档案整档导入前端闭环；设置 JSON 白名单导入

## 验收范围

- **R64 档案候选整档导入前端闭环**：旧档案预览面板接入既有后端 `POST /api/profiles/import`，
  整档导入为规则，前端展示导入 / 拒绝报告，成功后刷新规则清单与档案清单。后端本切片零改动。
- **R65 设置 JSON 白名单导入**：选择本地设置 JSON，仅采信连接地址与外部模型目录白名单键，
  填充当前表单而不直接写库；managed 路径与数据根不采信，结构非法保守提示；落库走既有
  `POST /api/settings` 白名单校验。后端本切片零改动。
- 基线：health `0.1.0-dev.5` / Python 3.13.18；`rules=0`，`profiles=13`；
  Ollama `127.0.0.1:11434`、ComfyUI `127.0.0.1:8188` 在线。

## R64 实现要点（`frontend/src/App.tsx` / `styles.css`）

- 新增 `ProfileImportReport` / `ProfileImportRejected` 类型；状态 `importingProfile`、
  `importReports`。
- `importProfile(file)`：调 `POST /api/profiles/import`（`{file_name}`），存报告；成功后单独
  刷新 `/api/rules` 与 `/api/profiles`，不覆盖 settings 等其他状态；消息按拒绝条数反馈。
- 预览展开区底部「整档导入为规则」按钮：候选非空且无解析错误时可点，导入中禁用并显示
  「正在导入…」；报告区显示已导入计数，拒绝项逐条列 `rule_key` + `reason`。
- 面板标题由「旧档案候选（只读）」改为「旧档案候选」；说明逐候选勾选 / 驳回 / 差异预览
  留后续版本。
- 未实现：逐候选勾选 / 驳回、差异预览（既有 backlog，未在本切片扩范围）。

## R65 实现要点（`frontend/src/App.tsx`）

- 隐藏文件输入 + `settingsFileRef`；`importSettingsFile(event)` 读取文件 → `JSON.parse`，
  根节点必须为对象（数组、非对象、解析失败均保守报错）。
- 白名单提取：
  - 连接：`ollama_url` / `comfyui_url`，值须字符串且 `http://` / `https://` 前缀，去尾斜杠；
    其他 scheme 或非字符串忽略该键。
  - 外部目录：`checkpoint` / `lora` / `clip` / `vae`，值须字符串。
  - managed 存储键与 `root` 不采信（由当前数据根重建）；未知键忽略。
- 合并进当前 `settings` 表单，提示「已从文件载入 N 项；请检查后点保存设置落库」；不直接写库。

## 真机闭环（本机 127.0.0.1:17890，PID 7328）

### R64

- 展开 `Anything_V5.txt`（SD1.5，候选 11），点「整档导入为规则」；后端 `POST /api/profiles/import`
  返回 200，报告「已导入 12 条规则」，无拒绝项。
- 直连 `/api/rules` 核对入库 12 条：architecture 2（`ARCHITECTURE::Base Architecture`、
  `ARCHITECTURE::Model Type`），checkpoint 10（IDENTITY / GENERATION SETTINGS / MODEL BEHAVIOR /
  CONFIDENCE / PROMPT STYLE 各键）。
- 截图：`acceptance-r64-candidates.png`（候选预览）、`acceptance-r64-report.png`（导入按钮与
  「已导入 12 条规则」报告框）。

### R65

- 测试导入 JSON 同时放入：合法外部目录（checkpoint、lora）、`clip` 非字符串（12345）、
  伪造 managed 路径与 `root`、`comfyui_url` 非法 scheme（`ftp://…`）、`ollama_url` 带尾斜杠。
- 导入后表单：checkpoint / lora 被填充；clip 保持空；managed `database` / `root` 保持基线
  未被伪造路径覆盖；`comfyui_url` 保留原值（ftp 被忽略）；`ollama_url` 去尾斜杠后填充。
- 消息「已从文件载入 3 项配置；请检查后点保存设置落库」。
- 直连 `/api/settings` 前后一致：外部目录仍为空、连接地址未变——导入只填充表单，未落库。
- 坏结构（根节点为数组）上传，保守提示「设置导入失败：Error: 设置文件根节点必须是对象」。
- 截图：`acceptance-r65-settings-import.png`（连接地址、导入 / 导出按钮与载入提示）。

## 收尾

- 冒烟产生的 12 条规则经 `DELETE /api/rules` 逐条回收，`rules` 归零；Ollama、ComfyUI 外部进程
  未触碰。
- stopper 按结构化身份回收实例（PID 7328，含子进程），端口 17890 关闭，运行记录清理。

## 回归

- 后端：**225 passed, 1 warning**（`pytest-output.txt`；StarletteDeprecationWarning 为遗留，
  与本项目无关）。本切片后端零改动，沿用既有 225 基线。
- 前端：`tsc -b && vite build` 绿（`frontend-build.txt`）；产物
  `index-B6npdTFA.js` 180.02 kB / gzip 57.49 kB，`index-X0JFovQF.css` 9.42 kB / gzip 2.33 kB。

## 边界与遗留

- R64 仅整档导入；逐候选勾选 / 驳回、差异预览、候选审核写入深化仍属 M3 backlog。
- R65 只做表单填充，不做导入前后差异对照；外部目录存在性与连接合法性由后端保存时 fail-closed
  校验，前端不重复判定。
- 未改动白名单写入、CSRF、回环绑定、unknown 不臆测等安全口径。
