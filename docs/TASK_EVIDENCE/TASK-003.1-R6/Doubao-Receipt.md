# 豆包回执 — TASK-003.1-R6

## 用户授权口径

- 由豆包在本机独立完成编码、自测、归档与 Git 操作；用户只做最终验收，不逐行审查。
- 交付形态：免安装本机 Web（FastAPI 同源托管 127.0.0.1，双击 bat 启停），不做 EXE / Tauri / Rust 打包。
- 端口：工作台 17890（避开 Ollama 11434、ComfyUI 8188 与酒馆）。

## 本轮完成

### M3 第一切片：模型清单只读对接

1. 后端新增 `backend/model_catalog.py`：
   - 从 ComfyUI `/object_info` 提取 Checkpoint / CLIP / VAE / LoRA 四组在册文件名；
   - 配置外部目录后只读核对文件名存在性（`on_disk` true/false）；未配置目录标记 `null`；
   - ComfyUI 不可达返回离线结构与错误文本，不抛 500。
2. `backend/main.py` 新增 `GET /api/models/catalog`（需本地会话）。
3. `backend/test_model_catalog.py` 新增 5 例回归；后端 **69 passed**。
4. 前端设置页新增「模型清单（只读）」面板：三列展示 Checkpoint / LoRA / VAE 与存在性状态；离线显示错误；响应式布局。前端 `tsc -b && vite build` **exit 0**。

### 真机验收

- 工作台 PID 12076，`/api/models/catalog`：online=true，Checkpoint 13、CLIP 0、VAE 3、LoRA 3。
- 指向真实 `models\checkpoints`、`models\loras` 核对：13 checkpoint、3 LoRA 全部 `on_disk=true`；核对后设置恢复空串。
- 浏览器截图两张归档：`model-catalog.png`、`model-catalog-list.png`。

### 进程处理

- 旧实例 PID 13660 因代码分组变更需重启；停止脚本既有身份校验缺陷未能自动回收，手动核对身份后回收根进程 13660 与工作子进程 8224，清理运行记录；ComfyUI、Ollama 未触碰，复核均 200。

## 未完成（明确边界）

- SHA256 身份库、三级规则继承、规则来源/可信度/版本/回退、冲突检测、动态检索、云端资料导入审核：后续 M3 切片。
- Ollama 对话生成（M4）、ComfyUI 出图提交/队列/进度/结果/输出目录索引（M6）：未实现。
- main 分支未改动；改动全部落在 dev。

## 自测结论

- 后端 69 passed, 1 warning（既有遗留警告）；前端构建 exit 0；真机清单拉取、分组、存在性核对、页面渲染与未授权拦截均通过。
