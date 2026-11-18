# TASK-003.1-R74 多命名草稿后端模型与接口

## 验收范围

- 拍板口径（R73 第 81.1 节）：草稿按**多份独立命名草稿**实现，每工作流独立草稿箱；
  不做单草稿 + 版本链。本切片落地后端存储模型、服务层与四个 HTTP 端点；前端草稿箱见 R75。
- 基线：`rules=0`、`history=0`、`tasks=0`、`profiles=13`、`workflows=22`、`model_identities=16`。

## 存储模型（`workflow_service.py` `WorkflowStore`）

- 每工作流 UUID 文件夹下新增 `drafts/<draft_uuid>.json`，记录
  `{id, name, positive, negative, note, created_at, updated_at}`。
- 草稿与单份 `working.json`、`versions/` 自动快照三者**相互独立**：保存草稿不触碰
  `working.json`，也不写版本快照；草稿载入工作副本仍走既有受保护 `write_prompts` 路径。
- 模块级常量：`MAX_DRAFT_NAME_CHARS=120`、`MAX_DRAFT_NOTE_CHARS=1000`；正/负向沿用
  `MAX_PROMPT_CHARS` 上限。

## 服务层方法

- `_drafts_dir(workflow_id)`：UUID 工作流目录越界防护。
- `_draft_path(drafts_dir, draft_id)`：draft_id 走 UUID 校验 + 路径越界防护。
- `_read_draft_file(path)`：损坏/缺字段文件保守跳过。
- `list_drafts(workflow_id)`：按 `updated_at` 倒序；损坏文件跳过不拖垮整列。
- `save_draft(...)`：`draft_id` 空→新建 UUID，非空→更新；名称 strip 后非空且 ≤120；
  备注 ≤1000；正/负向两侧都空拒绝；同工作流同名去重（更新自身除外）。
- `get_draft(workflow_id, draft_id)`：读取单条完整草稿。
- `delete_draft(workflow_id, draft_id)`：删除单条；生成历史与图片不触碰。

## HTTP 端点（`workflow_api.py`，前缀 `/api/workflows`）

- `DraftSave`：`draft_id?: str|null`、`name`（min_length 1 / max_length 120 + strip 非空
  validator）、`positive?/negative?/note?`。
- `GET /{workflow_id}/drafts`：列出草稿（最新更新在前）。
- `POST /{workflow_id}/drafts`：新建或更新草稿；不写工作副本。
- `GET /{workflow_id}/drafts/{draft_id}`：读取单条完整草稿。
- `DELETE /{workflow_id}/drafts/{draft_id}`：删除单条。
- 错误经既有 `_raise_api_error` 映射 400 / 404 / 500；鉴权与 CSRF 口径沿用既有中间件。

## 测试

- 服务层 4 例（`test_workflow_service.py`）：
  - `test_draft_create_list_read_does_not_touch_working`：建/列/读不改 working 与 versions。
  - `test_draft_update_rejects_duplicate_name_and_missing`：更新、同名拒绝、非法 UUID、不存在。
  - `test_draft_delete_and_isolation_between_workflows`：删除与跨工作流隔离。
  - `test_draft_rejects_empty_prompt_and_blank_name`：空 Prompt 与空名拒绝。
- API 层 2 例（`test_workflow_tasks.py`）：
  - `test_draft_create_read_update_delete_roundtrip`：建/读/更新/删除往返。
  - `test_draft_rejects_empty_prompt_duplicate_name_and_missing`：空 Prompt 400、重名 400、
    不存在工作流 404。
- 全量回归：**237 passed, 1 warning**（`pytest-output.txt`；StarletteDeprecationWarning
  为遗留，与本项目无关）。

## 边界与遗留

- 最小闭环仅含新建 / 列出 / 载入 / 删除 + 备注；收藏、标签、搜索、跨工作流复制草稿、
  回收站、模型环境快照、对话上下文 / 锁定片段、草稿与生成历史双向索引、由历史反向创建草稿
  等留后续切片评估。
- 未改动白名单写入、CSRF、回环绑定、unknown 不臆测、冲突人工核对等安全口径。
