# Doubao 回执 — TASK-003.1-R16

## 任务

ComfyUI Prompt Workbench，M3 第十一切片：架构级规则随档案导入（分节分流，本地 FastAPI + React 免安装本机 Web）。

## 执行结果

- 候选投影按分节分流：ARCHITECTURE 节事实落 architecture 级（scope=解析出的底座标签），其余节落 checkpoint 级（scope=完整 checkpoint 文件名）。
- 导入按记录自带 level/scope 落库；无底座标签的架构字段无法确定作用域，记入 rejected，不擅自归 checkpoint 或 global；引擎层级/继承/冲突口径不变。
- 后端 pytest **119 passed**（1 条既有 StarletteDeprecationWarning）；前端 `tsc -b && vite build` exit 0（33 模块）。
- 真机闭环：Anything_V5 导入 11 条，9 条 checkpoint + 2 条 architecture(SD1.5)；checkpoint 上下文解析架构字段为 unknown；两类规则清理归零，见 `samples/smoke-levels.json`。

## 交付边界

- global 级规则本轮不装载：旧档案暂无跨模型通用事实来源。
- 架构标签为散文标签，未做归一化/同义归并；结构化参数前端展示、跨模型继承真机装配、逐候选审核界面未实现。
- 未对接 Ollama 对话生成（M4）、ComfyUI 出图对接（M6）；未改动 main 分支，改动落在 dev。

## 提交信息

- 分支：`dev`
- 提交：`dd447194c8c9c2dab7683b9f2be5ba18d14dc0f1`（本地 commit，已推送 origin/dev，连接器核对远端 dev 最新即此提交）。
- 基线：`d601345`（R15 回执回填）。
