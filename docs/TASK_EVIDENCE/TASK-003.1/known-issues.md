# TASK-003.1 已知问题（待 ChatGPT 侧确认 / 修正）

分工口径：代码由 ChatGPT 提供，豆包只落盘、跑测、反馈；以下问题豆包未自行重写核心实现。

## P1（阻塞）后端 API workflow 结构口径不一致：解析器取 `workflow["nodes"]`，测试样本为扁平根结构

### 现象
`backend/test_workflow_service.py` 的 `sample_api_workflow()` 是 ComfyUI 标准 API prompt 扁平结构，节点直接挂在根对象下：

```json
{
  "1": {"class_type": "CLIPTextEncode", "inputs": {"text": "old positive", "clip": ["3", 0]}},
  "2": {"class_type": "CLIPTextEncode", "inputs": {"text": "old negative", "clip": ["3", 0]}},
  "3": {"class_type": "CLIPLoader", "inputs": {"clip_name": "text_encoder.safetensors"}},
  "4": {"class_type": "LoraLoader", "inputs": {"lora_name": "sample_lora.safetensors", ...}},
  "5": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "..."}},
  "6": {"class_type": "KSampler", "inputs": {"seed": 123456, ..., "positive": ["1", 0], "negative": ["2", 0]}}
}
```

而 `backend/workflow_service.py` 的格式识别与节点读取都从 `workflow["nodes"]` 取值：

- `detect_format`（落盘 `workflow_service.py` 第 63–80 行；源码任务书第 90–111 行）：
  `nodes = workflow.get("nodes")`，只有当 `nodes` 是 dict 且各项带 `class_type` 才判为 `api`。扁平样本根下没有 `nodes` 键，落入最后的 `WorkflowError`。
- `_api_nodes`（第 81–85 行；源码第 113–117 行）：
  `nodes = workflow.get("nodes")`，不是 dict 就抛 `WorkflowError("API workflow 缺少 nodes 对象")`。

### 失败测试与错误原文
6 个失败用例均在 `detect_format` / `import_workflow` 阶段被拒，统一错误：

```
workflow_service.WorkflowError: 无法识别工作流格式。请导入 ComfyUI API workflow 或 UI workflow JSON。
```

- `test_detect_api_workflow`（test 第 60 行）：`assert detect_format(sample_api_workflow()) == "api"`
- `test_api_parser_finds_prompt_roles_models_and_lora`（第 62 行）：`analyze_workflow(...)`
- `test_prompt_write_changes_only_confirmed_text_fields`（第 79 行）：`store.import_workflow(...)`
- `test_write_rejects_unconfirmed_nodes`（第 120 行）：同上
- `test_write_rejects_non_whitelist_mutation`（第 132 行）：同上
- `test_write_rejects_changed_original_fingerprint`（第 159 行）：同上

### 需要 ChatGPT 侧确认的口径
二选一（不要豆包自行定方向）：

1. **解析器适配扁平 API prompt**：`detect_format` 识别「根对象值均为带 `class_type`/`inputs` 的 dict」的结构为 `api`；`_api_nodes` 在无 `nodes` 键时直接返回根对象。
2. **测试样本改为带 `nodes` 包裹的结构**：即样本根下增加 `"nodes": {"1": ..., ...}`，与现有解析器对齐。

> 备注：ComfyUI `/prompt` 提交用的 API prompt 通常是扁平结构（节点 ID 为根键）；当前解析器的 `nodes` 键写法更接近 UI workflow 的容器形态。请确认目标支持的真实导出格式后统一口径。

### 潜在连带点（待解析口径确定后复测，不预先改）
- `WorkflowStore.get_workflow` 中 `nodes = _api_nodes(working)` 同样依赖 `_api_nodes`。
- `confirm_prompt_nodes` / `write_prompts` 内的 `nodes_original` / `nodes_working` 也走 `_api_nodes`。
- 若解析器改为扁平结构，上述函数的节点取值需一并保持一致。

## P2（待复测）API 写入链路尚未走到

在 P1 修复前，以下用例的预期行为无法验证，不能视为已通过：

- 只改已确认白名单 `inputs.text`，原始文件不变、其他字段不变、`versions/` 生成快照。
- 未确认节点写入被拒绝。
- 工作副本存在非白名单变化时被拒绝（匹配「非白名单」）。
- 原始指纹变化时被拒绝（匹配「指纹」）。

## P3（环境备注，非代码缺陷）

- 本机无 Python 3.12，仅在 `.venv` Python 3.13.18 下执行；3.12 兼容性未验证。
- 后端启动时存在 Starlette/httpx 弃用告警（`StarletteDeprecationWarning`，建议安装 `httpx2`），为既有依赖版本提示，非本次新增。
- 未做 Ollama 接入、自动出图、ComfyUI 队列等任务范围外事项。
