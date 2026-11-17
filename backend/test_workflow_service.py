import json
import pytest
from workflow_service import (
    WorkflowError,
    WorkflowStore,
    analyze_workflow,
    detect_format,
)
def sample_api_workflow():
    return {
        "1": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "old positive",
                "clip": ["3", 0],
            },
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "old negative",
                "clip": ["3", 0],
            },
        },
        "3": {
            "class_type": "CLIPLoader",
            "inputs": {
                "clip_name": "text_encoder.safetensors",
            },
        },
        "4": {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": "sample_lora.safetensors",
                "strength_model": 0.8,
                "strength_clip": 0.7,
                "model": ["5", 0],
                "clip": ["3", 0],
            },
        },
        "5": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": "sample_checkpoint.safetensors",
            },
        },
        "6": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 123456,
                "steps": 24,
                "cfg": 6.5,
                "positive": ["1", 0],
                "negative": ["2", 0],
                "model": ["4", 0],
            },
        },
    }
def test_detect_api_workflow():
    assert detect_format(sample_api_workflow()) == "api"
def test_api_parser_finds_prompt_roles_models_and_lora():
    report = analyze_workflow(sample_api_workflow())
    assert report["format"] == "api"
    assert report["safe_prompt_write_supported"] is True
    roles = {
        item["node_id"]: item["roles"]
        for item in report["prompt_nodes"]
    }
    assert roles["1"] == ["positive"]
    assert roles["2"] == ["negative"]
    model_types = {item["class_type"] for item in report["model_nodes"]}
    assert "CLIPLoader" in model_types
    assert "CheckpointLoaderSimple" in model_types
    assert len(report["lora_nodes"]) == 1
    assert report["lora_nodes"][0]["node_id"] == "4"
def test_prompt_write_changes_only_confirmed_text_fields(tmp_path):
    store = WorkflowStore(tmp_path / "workflows")
    source = sample_api_workflow()
    imported = store.import_workflow("sample_api.json", source)
    workflow_id = imported["id"]
    store.confirm_prompt_nodes(
        workflow_id,
        positive_node_ids=["1"],
        negative_node_ids=["2"],
    )
    result = store.write_prompts(
        workflow_id,
        positive_text="new positive prompt",
        negative_text="new negative prompt",
    )
    assert result["ok"] is True
    assert len(result["changes"]) == 2
    original = json.loads(
        (tmp_path / "workflows" / workflow_id / "original.json")
        .read_text(encoding="utf-8")
    )
    working = json.loads(
        (tmp_path / "workflows" / workflow_id / "working.json")
        .read_text(encoding="utf-8")
    )
    # The original file is never changed.
    assert original == source
    assert original["1"]["inputs"]["text"] == "old positive"
    assert original["2"]["inputs"]["text"] == "old negative"
    # Only the two explicitly whitelisted text fields are different.
    assert working["1"]["inputs"]["text"] == "new positive prompt"
    assert working["2"]["inputs"]["text"] == "new negative prompt"
    assert working["6"]["inputs"]["seed"] == 123456
    assert working["6"]["inputs"]["steps"] == 24
    assert working["6"]["inputs"]["cfg"] == 6.5
    assert working["5"] == original["5"]
    assert working["4"] == original["4"]
    versions = (
        tmp_path / "workflows" / workflow_id / "versions"
    )
    assert versions.is_dir()
    assert list(versions.glob("*.json"))
def test_write_rejects_unconfirmed_nodes(tmp_path):
    store = WorkflowStore(tmp_path / "workflows")
    imported = store.import_workflow(
        "sample_api.json",
        sample_api_workflow(),
    )
    with pytest.raises(WorkflowError):
        store.write_prompts(
            imported["id"],
            positive_text="should not write",
            negative_text=None,
        )
def test_write_rejects_non_whitelist_mutation(tmp_path):
    store = WorkflowStore(tmp_path / "workflows")
    imported = store.import_workflow(
        "sample_api.json",
        sample_api_workflow(),
    )
    workflow_id = imported["id"]
    store.confirm_prompt_nodes(
        workflow_id,
        positive_node_ids=["1"],
        negative_node_ids=["2"],
    )
    working_file = (
        tmp_path / "workflows" / workflow_id / "working.json"
    )
    working = json.loads(working_file.read_text(encoding="utf-8"))
    working["6"]["inputs"]["seed"] = 999999
    working_file.write_text(
        json.dumps(working, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with pytest.raises(WorkflowError, match="非白名单"):
        store.write_prompts(
            workflow_id,
            positive_text="must be rejected",
            negative_text=None,
        )
def test_write_rejects_changed_original_fingerprint(tmp_path):
    store = WorkflowStore(tmp_path / "workflows")
    imported = store.import_workflow(
        "sample_api.json",
        sample_api_workflow(),
    )
    workflow_id = imported["id"]
    store.confirm_prompt_nodes(
        workflow_id,
        positive_node_ids=["1"],
        negative_node_ids=["2"],
    )
    original_file = (
        tmp_path / "workflows" / workflow_id / "original.json"
    )
    original = json.loads(original_file.read_text(encoding="utf-8"))
    original["6"]["inputs"]["seed"] = 999
    original_file.write_text(
        json.dumps(original, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with pytest.raises(WorkflowError, match="指纹"):
        store.write_prompts(
            workflow_id,
            positive_text="must be rejected",
            negative_text=None,
        )
def test_ui_workflow_is_parsed_but_not_writable():
    ui_workflow = {
        "nodes": [
            {
                "id": 1,
                "type": "CLIPTextEncode",
                "inputs": [],
                "widgets_values": ["example prompt"],
            }
        ],
        "links": [],
    }
    assert detect_format(ui_workflow) == "ui"
    report = analyze_workflow(ui_workflow)
    assert report["format"] == "ui"
    assert report["safe_prompt_write_supported"] is False
    assert report["prompt_nodes"][0]["node_id"] == "1"
    assert report["prompt_nodes"][0]["editable"] is False
def test_invalid_workflow_is_rejected():
    with pytest.raises(WorkflowError):
        detect_format({"hello": "world"})
def test_import_rejects_oversized_workflow(tmp_path):
    store = WorkflowStore(tmp_path / "workflows")
    huge = {
        "1": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "x" * (21 * 1024 * 1024)},
        }
    }
    with pytest.raises(WorkflowError, match="20 MB"):
        store.import_workflow("too-large.json", huge)
