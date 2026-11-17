from __future__ import annotations
from pathlib import Path
from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import datadir
from workflow_service import WorkflowError, WorkflowStore
router = APIRouter(prefix="/api/workflows", tags=["workflows"])
def store() -> WorkflowStore:
    return WorkflowStore(datadir.default_data_root() / "workflows")
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
