from __future__ import annotations
import uuid
from pathlib import Path
from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
import comfy_client
import comfy_tasks
import datadir
import llm_client
import model_identity
import rule_compare
import rule_prompt
import rule_store
from workflow_service import WorkflowError, WorkflowStore
router = APIRouter(prefix="/api/workflows", tags=["workflows"])
def store() -> WorkflowStore:
    return WorkflowStore(datadir.default_data_root() / "workflows")
def _database_path() -> Path:
    return datadir.database_path(datadir.default_data_root())
def _sampler_actuals(report: dict[str, Any]) -> dict[str, Any]:
    """Merge the first sampler group's scalar params and latent size for comparison.

    Multi-group workflows are reported conservatively: the top-level actuals
    keep the first group's params, while every group's params are listed under
    ``sampler_groups``. Later groups are never merged into the first group's
    verdict; a per-group comparison is a later slice.
    """
    actuals: dict[str, Any] = {}
    sampler_groups: list[dict[str, Any]] = []
    for group in report.get("prompt_groups", []):
        params = group.get("params")
        if not isinstance(params, dict):
            params = {}
        sampler_groups.append(
            {"sampler_node_id": group.get("sampler_node_id"), "params": params}
        )
        if params and not actuals:
            actuals.update(params)
    actuals["sampler_group_count"] = len(sampler_groups)
    actuals["sampler_groups"] = sampler_groups
    latent = report.get("latent")
    if isinstance(latent, dict):
        if latent.get("width") is not None:
            actuals["width"] = latent["width"]
        if latent.get("height") is not None:
            actuals["height"] = latent["height"]
    clip_skip = report.get("clip_skip")
    if isinstance(clip_skip, dict) and clip_skip.get("clip_skip") is not None:
        actuals["clip_skip"] = clip_skip["clip_skip"]

    latent_nodes = report.get("latent_nodes")
    if isinstance(latent_nodes, list):
        actuals["latent_node_count"] = len(latent_nodes)
        actuals["latent_nodes"] = [
            {
                "node_id": node.get("node_id"),
                "width": node.get("width"),
                "height": node.get("height"),
            }
            for node in latent_nodes
            if isinstance(node, dict)
        ]
    clip_nodes = report.get("clip_skip_nodes")
    if isinstance(clip_nodes, list):
        actuals["clip_skip_node_count"] = len(clip_nodes)
        actuals["clip_skip_nodes"] = [
            {
                "node_id": node.get("node_id"),
                "clip_skip": node.get("clip_skip"),
            }
            for node in clip_nodes
            if isinstance(node, dict)
        ]
    return actuals


def _checkpoint_filename(report: dict[str, Any]) -> str | None:
    """Extract the first checkpoint file name recognized in the workflow."""
    for node in report.get("model_nodes", []):
        inputs = node.get("inputs", {})
        for key in ("ckpt_name", "unet_name"):
            value = inputs.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None
def _raise_api_error(exc: Exception) -> None:
    if isinstance(exc, FileNotFoundError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, WorkflowError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    raise HTTPException(status_code=500, detail="工作流处理失败") from exc
class WorkflowImport(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    workflow: dict[str, Any]
class PromptNodeConfirmation(BaseModel):
    positive_node_ids: list[str] = Field(default_factory=list)
    negative_node_ids: list[str] = Field(default_factory=list)
class PromptWrite(BaseModel):
    positive_text: str | None = None
    negative_text: str | None = None


class PromptCandidateRequest(BaseModel):
    model: str = Field(min_length=1, max_length=120)
    task: str | None = Field(default=None, max_length=2000)

    @field_validator("model")
    @classmethod
    def _model_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("model must not be blank")
        return value.strip()


def _ollama_url() -> str:
    """Read the configured local Ollama URL, falling back to the default."""
    root = datadir.default_data_root()
    settings = datadir.default_settings(root)
    loaded = datadir.load_settings_file(root)
    if isinstance(loaded, dict):
        connections = loaded.get("connections")
        if isinstance(connections, dict) and isinstance(
            connections.get("ollama_url"), str
        ):
            return connections["ollama_url"].rstrip("/")
    return settings["connections"]["ollama_url"].rstrip("/")


def _comfyui_url() -> str:
    """Read the configured local ComfyUI URL, falling back to the default."""
    root = datadir.default_data_root()
    settings = datadir.default_settings(root)
    loaded = datadir.load_settings_file(root)
    if isinstance(loaded, dict):
        connections = loaded.get("connections")
        if isinstance(connections, dict) and isinstance(
            connections.get("comfyui_url"), str
        ):
            return connections["comfyui_url"].rstrip("/")
    return settings["connections"]["comfyui_url"].rstrip("/")


def _unregistered_context() -> dict[str, Any]:
    return {
        "status": "unregistered",
        "checkpoint": None,
        "architecture": None,
        "architecture_family": None,
        "architecture_label": None,
        "checkpoint_rules": [],
        "architecture_rules": [],
        "global_rules": [],
    }


def _rules_system_message(rule_payload: dict[str, Any]) -> str:
    lines: list[str] = [rule_payload.get("instruction", "")]
    fields = rule_payload.get("fields", [])
    if fields:
        lines.append("已解析规则：")
        for entry in fields:
            lines.append(
                f"- {entry.get('key')}: {entry.get('value')}（{entry.get('status')}）"
            )
    if rule_payload.get("conflicts"):
        lines.append("存在 conflict 字段，需人工核对，不要替模型选择。")
    if rule_payload.get("unknown"):
        lines.append("存在 unknown 字段，不要补默认值或猜测。")
    return "\n".join(line for line in lines if line)


def _user_message(
    working_prompts: list[dict[str, Any]], task: str | None
) -> str:
    by_role: dict[str, list[str]] = {"positive": [], "negative": []}
    for item in working_prompts:
        role = item.get("role")
        text = item.get("text")
        if role in by_role and isinstance(text, str) and text.strip():
            by_role[role].append(text.strip())

    lines: list[str] = ["当前工作流现有 Prompt："]
    if by_role["positive"]:
        lines.append("正向：" + " / ".join(by_role["positive"]))
    if by_role["negative"]:
        lines.append("负向：" + " / ".join(by_role["negative"]))
    if task and task.strip():
        lines.append(f"任务要求：{task.strip()}")
    lines.append(
        "请基于上述规则与现有内容给出 Prompt 候选；未提供的参数不要臆造。"
    )
    return "\n".join(lines)
@router.get("")
def list_workflows():
    return {"items": store().list_workflows()}
@router.post("/import")
def import_workflow(payload: WorkflowImport):
    try:
        return store().import_workflow(payload.filename, payload.workflow)
    except (WorkflowError, OSError) as exc:
        _raise_api_error(exc)
@router.get("/{workflow_id}")
def get_workflow(workflow_id: str):
    try:
        return store().get_workflow(workflow_id)
    except (WorkflowError, FileNotFoundError, OSError) as exc:
        _raise_api_error(exc)
@router.post("/{workflow_id}/confirm")
def confirm_prompt_nodes(
    workflow_id: str,
    payload: PromptNodeConfirmation,
):
    try:
        return store().confirm_prompt_nodes(
            workflow_id,
            payload.positive_node_ids,
            payload.negative_node_ids,
        )
    except (WorkflowError, FileNotFoundError, OSError) as exc:
        _raise_api_error(exc)
@router.post("/{workflow_id}/write")
def write_prompts(workflow_id: str, payload: PromptWrite):
    try:
        return store().write_prompts(
            workflow_id,
            payload.positive_text,
            payload.negative_text,
        )
    except (WorkflowError, FileNotFoundError, OSError) as exc:
        _raise_api_error(exc)


@router.get("/{workflow_id}/rules")
def workflow_rule_context(workflow_id: str):
    """Return only the rules relevant to this workflow's checkpoint context.

    The recognized checkpoint filename is matched exactly against stored
    checkpoint rules; architecture and global rules are attached for programmatic
    inheritance. Unrelated stored rules are never returned. A workflow with no
    recognized checkpoint, or a checkpoint with no stored rule, is reported
    ``unregistered`` with an empty rule set; the engine never fabricates a rule.
    """
    try:
        workflow = store().get_workflow(workflow_id)
    except (WorkflowError, FileNotFoundError, OSError) as exc:
        _raise_api_error(exc)

    report = workflow.get("report", {})
    checkpoint = _checkpoint_filename(report)
    if not checkpoint:
        return {
            "status": "unregistered",
            "reason": "no_checkpoint_recognized",
            "checkpoint": None,
            "architecture": None,
            "architecture_family": None,
            "architecture_label": None,
            "checkpoint_rules": [],
            "architecture_rules": [],
            "global_rules": [],
        }

    with model_identity.connect(_database_path()) as connection:
        rule_store.ensure_schema(connection)
        context = rule_store.context_for_checkpoint(connection, checkpoint)
    return context


@router.get("/{workflow_id}/rules/prompt")
def workflow_rule_prompt(workflow_id: str):
    """Assemble the trimmed, LLM-ready rule prompt payload for this workflow.

    Resolves the R17 context through the engine's programmatic inheritance and
    keeps the winning source, provenance and confidence per field. Conflicts
    stay marked ``conflict`` and uncovered fields ``unknown``; the downstream
    model is never asked to guess a value or inheritance priority. Unregistered
    workflows return an empty payload with a no-guidance instruction.
    """
    try:
        workflow = store().get_workflow(workflow_id)
    except (WorkflowError, FileNotFoundError, OSError) as exc:
        _raise_api_error(exc)

    report = workflow.get("report", {})
    checkpoint = _checkpoint_filename(report)
    if not checkpoint:
        return rule_prompt.build_prompt_context(
            {
                "status": "unregistered",
                "checkpoint": None,
                "architecture": None,
                "architecture_family": None,
                "architecture_label": None,
                "checkpoint_rules": [],
                "architecture_rules": [],
                "global_rules": [],
            }
        )

    with model_identity.connect(_database_path()) as connection:
        rule_store.ensure_schema(connection)
        context = rule_store.context_for_checkpoint(connection, checkpoint)
    return rule_prompt.build_prompt_context(context)


@router.post("/{workflow_id}/prompt/candidates")
def prompt_candidates(workflow_id: str, payload: PromptCandidateRequest):
    """Ask the local Ollama model for a prompt candidate for this workflow.

    Only the trimmed rule context already resolved for this workflow is sent;
    unrelated rules are never included. The response is a candidate text only:
    it is not written back to the workflow, and the working draft is left
    untouched. A local-model failure returns a conservative 502 with no
    fabricated candidate; there is no cloud fallback.
    """
    try:
        workflow = store().get_workflow(workflow_id)
    except (WorkflowError, FileNotFoundError, OSError) as exc:
        _raise_api_error(exc)

    report = workflow.get("report", {})
    checkpoint = _checkpoint_filename(report)
    if checkpoint:
        with model_identity.connect(_database_path()) as connection:
            rule_store.ensure_schema(connection)
            context = rule_store.context_for_checkpoint(connection, checkpoint)
    else:
        context = _unregistered_context()
    rule_payload = rule_prompt.build_prompt_context(context)

    messages = [
        {"role": "system", "content": _rules_system_message(rule_payload)},
        {
            "role": "user",
            "content": _user_message(workflow.get("working_prompts", []), payload.task),
        },
    ]
    result = llm_client.chat(_ollama_url(), payload.model, messages)
    if not result["ok"]:
        raise HTTPException(
            status_code=502,
            detail={"online": False, "error": result["error"]},
        )

    return {
        "model": result["model"],
        "candidates": [result["content"]],
        "rule_status": rule_payload["status"],
        "conflicts": rule_payload["conflicts"],
        "unknown": rule_payload["unknown"],
    }


@router.post("/{workflow_id}/tasks")
def submit_task(workflow_id: str):
    """Submit the working API-format workflow to local ComfyUI, guarded.

    The submission fails closed: ComfyUI must be reachable, the workflow must
    already be in API format, the Prompt-node whitelist must be confirmed, and
    the local LLM must be confirmed unloaded (or unreachable means unknown, so
    it is rejected too). UI-format workflows cannot be converted here and are
    rejected. A failed submit records no local task; retries are manual.
    """
    try:
        workflow = store().get_workflow(workflow_id)
    except (WorkflowError, FileNotFoundError, OSError) as exc:
        _raise_api_error(exc)

    manifest = workflow.get("manifest", {})
    if manifest.get("format") != "api":
        raise HTTPException(
            status_code=400,
            detail="UI 格式工作流不能直接提交，请先在 ComfyUI 中导出 API 格式。",
        )
    if not manifest.get("confirmed"):
        raise HTTPException(
            status_code=400,
            detail="请先确认 Prompt 节点白名单，再提交任务。",
        )

    comfyui_url = _comfyui_url()
    ollama_url = _ollama_url()

    if not comfy_client.comfyui_online(comfyui_url):
        raise HTTPException(
            status_code=502,
            detail={"online": False, "error": "ComfyUI 不可达，未提交任务。"},
        )

    loaded = comfy_client.loaded_ollama_models(ollama_url)
    if not loaded["online"]:
        raise HTTPException(
            status_code=502,
            detail={"online": False, "error": "无法确认本地 LLM 已卸载，未提交任务。"},
        )
    if loaded["models"]:
        raise HTTPException(
            status_code=409,
            detail={
                "online": True,
                "loaded": loaded["models"],
                "error": "本地 LLM 仍驻留显存，请先卸载后再提交。",
            },
        )

    working = store().read_working(workflow_id)
    client_id = str(uuid.uuid4())
    result = comfy_client.submit_prompt(comfyui_url, working, client_id)
    if not result["ok"]:
        raise HTTPException(
            status_code=502,
            detail={
                "online": True,
                "error": result["error"],
                "node_errors": result["node_errors"],
            },
        )

    with model_identity.connect(_database_path()) as connection:
        comfy_tasks.ensure_schema(connection)
        record = comfy_tasks.record_submission(
            connection,
            result["prompt_id"],
            workflow_id,
            result["node_errors"],
        )
    return record


@router.get("/{workflow_id}/tasks")
def list_tasks(workflow_id: str):
    """Return locally recorded tasks for this workflow, newest first."""
    try:
        store().get_workflow(workflow_id)
    except (WorkflowError, FileNotFoundError, OSError) as exc:
        _raise_api_error(exc)

    with model_identity.connect(_database_path()) as connection:
        comfy_tasks.ensure_schema(connection)
        return {
            "items": comfy_tasks.list_for_workflow(connection, workflow_id),
        }


@router.get("/{workflow_id}/rules/compare")
def workflow_rule_compare(workflow_id: str):
    """Compare the resolved rule payload against this workflow's sampler actuals.

    Only facts readable on both sides get a verdict; non-numeric actuals,
    non-structured rules and unrelated fields stay ``unknown`` rather than being
    guessed. Unregistered workflows return an empty comparison set.
    """
    try:
        workflow = store().get_workflow(workflow_id)
    except (WorkflowError, FileNotFoundError, OSError) as exc:
        _raise_api_error(exc)

    report = workflow.get("report", {})
    checkpoint = _checkpoint_filename(report)
    actuals = _sampler_actuals(report)
    if not checkpoint:
        payload = rule_prompt.build_prompt_context(
            {
                "status": "unregistered",
                "checkpoint": None,
                "architecture": None,
                "architecture_family": None,
                "architecture_label": None,
                "checkpoint_rules": [],
                "architecture_rules": [],
                "global_rules": [],
            }
        )
        return rule_compare.compare_workflow(payload, actuals)

    with model_identity.connect(_database_path()) as connection:
        rule_store.ensure_schema(connection)
        context = rule_store.context_for_checkpoint(connection, checkpoint)
    payload = rule_prompt.build_prompt_context(context)
    return rule_compare.compare_workflow(payload, actuals)
