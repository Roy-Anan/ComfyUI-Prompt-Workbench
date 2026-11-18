from __future__ import annotations
from pathlib import Path
from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import datadir
import model_identity
import rule_store
from workflow_service import WorkflowError, WorkflowStore
router = APIRouter(prefix="/api/workflows", tags=["workflows"])
def store() -> WorkflowStore:
    return WorkflowStore(datadir.default_data_root() / "workflows")
def _database_path() -> Path:
    return datadir.database_path(datadir.default_data_root())
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
            "checkpoint_rules": [],
            "architecture_rules": [],
            "global_rules": [],
        }

    with model_identity.connect(_database_path()) as connection:
        rule_store.ensure_schema(connection)
        context = rule_store.context_for_checkpoint(connection, checkpoint)
    return context
