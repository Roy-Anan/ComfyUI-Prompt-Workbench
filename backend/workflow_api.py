from __future__ import annotations
from pathlib import Path
from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import datadir
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
