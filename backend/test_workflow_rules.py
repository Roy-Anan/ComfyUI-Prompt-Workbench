import sqlite3

import rule_store


def _seed_context_rules(database_path):
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path, timeout=10)
    rule_store.ensure_schema(connection)
    rule_store.upsert_rule(
        connection, "checkpoint", "sample_checkpoint.safetensors",
        "ARCHITECTURE::Base Architecture", "SD1.5（哈希一致）",
        provenance="verified_mirror", confidence="partial",
    )
    rule_store.upsert_rule(
        connection, "checkpoint", "sample_checkpoint.safetensors",
        "GENERATION SETTINGS::Steps", "20",
        provenance="author", confidence="authoritative",
    )
    rule_store.upsert_rule(
        connection, "architecture", "SD1.5",
        "ARCHITECTURE::Model Type", "Checkpoint",
        provenance="author", confidence="partial",
    )
    rule_store.upsert_rule(connection, "global", None, "GENERATION SETTINGS::Scheduler", "Karras")
    # Unrelated checkpoint must not leak into this context.
    rule_store.upsert_rule(
        connection, "checkpoint", "other_checkpoint.safetensors",
        "GENERATION SETTINGS::Steps", "30",
    )
    connection.close()


def _import_sample(client, main, workflow):
    response = client.post(
        "/api/workflows/import",
        headers={"Authorization": "Bearer test-session-token"},
        json={"filename": "sample.json", "workflow": workflow},
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_workflow_rules_context_matches_checkpoint_and_inherits(client):
    test_client, main = client
    db = main.DATA_ROOT / "database" / "workbench.sqlite3"
    _seed_context_rules(db)

    workflow = {
        "5": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "sample_checkpoint.safetensors"}},
        "6": {"class_type": "KSampler", "inputs": {"positive": ["1", 0], "negative": ["2", 0]}},
    }
    workflow_id = _import_sample(test_client, main, workflow)

    response = test_client.get(
        f"/api/workflows/{workflow_id}/rules",
        headers={"Authorization": "Bearer test-session-token"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "registered"
    assert body["checkpoint"] == "sample_checkpoint.safetensors"
    assert body["architecture"] == "SD1.5"

    cp_keys = {item["rule_key"] for item in body["checkpoint_rules"]}
    assert "GENERATION SETTINGS::Steps" in cp_keys
    assert "ARCHITECTURE::Base Architecture" in cp_keys

    arch_keys = {item["rule_key"] for item in body["architecture_rules"]}
    assert "ARCHITECTURE::Model Type" in arch_keys

    global_keys = {item["rule_key"] for item in body["global_rules"]}
    assert "GENERATION SETTINGS::Scheduler" in global_keys

    # The Base Architecture fact was redirected to the architecture level on
    # import, so the checkpoint record itself may not carry it; the join must
    # still resolve the architecture scope from the architecture bucket.
    assert body["architecture"] == "SD1.5"

    # Unrelated checkpoint rule must be excluded.
    all_keys = cp_keys | arch_keys | global_keys
    assert "other_checkpoint.safetensors" not in str(body)


def test_workflow_rules_unregistered_for_unknown_checkpoint(client):
    test_client, main = client
    db = main.DATA_ROOT / "database" / "workbench.sqlite3"
    _seed_context_rules(db)

    workflow = {
        "5": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "ghost.safetensors"}},
    }
    workflow_id = _import_sample(test_client, main, workflow)

    response = test_client.get(
        f"/api/workflows/{workflow_id}/rules",
        headers={"Authorization": "Bearer test-session-token"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unregistered"
    assert body["checkpoint"] == "ghost.safetensors"
    assert body["checkpoint_rules"] == []
    assert body["architecture"] is None
    assert body.get("architecture_family") is None


def test_workflow_rule_prompt_payload_for_registered_workflow(client):
    test_client, main = client
    db = main.DATA_ROOT / "database" / "workbench.sqlite3"
    _seed_context_rules(db)

    workflow = {
        "5": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "sample_checkpoint.safetensors"}},
    }
    workflow_id = _import_sample(test_client, main, workflow)

    response = test_client.get(
        f"/api/workflows/{workflow_id}/rules/prompt",
        headers={"Authorization": "Bearer test-session-token"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "registered"
    assert body["checkpoint"] == "sample_checkpoint.safetensors"
    field_keys = {item["key"] for item in body["fields"]}
    assert "GENERATION SETTINGS::Steps" in field_keys
    assert any(f["source_level"] == "global" for f in body["fields"])
    assert "checkpoint 规则优先" in body["instruction"]


def test_workflow_rule_compare_against_sampler_actuals(client):
    test_client, main = client
    db = main.DATA_ROOT / "database" / "workbench.sqlite3"
    _seed_context_rules(db)

    workflow = {
        "5": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "sample_checkpoint.safetensors"}},
        "6": {
            "class_type": "KSampler",
            "inputs": {"steps": 20, "cfg": 7.0, "positive": ["1", 0], "negative": ["2", 0]},
        },
        "7": {"class_type": "EmptyLatentImage", "inputs": {"width": 704, "height": 1024, "batch_size": 1}},
        "8": {"class_type": "CLIPSetLastLayer", "inputs": {"clip": ["3", 0], "stop_at_clip_layer": -2}},
    }
    workflow_id = _import_sample(test_client, main, workflow)

    response = test_client.get(
        f"/api/workflows/{workflow_id}/rules/compare",
        headers={"Authorization": "Bearer test-session-token"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "registered"
    assert body["actuals"]["steps"] == 20
    assert body["actuals"]["width"] == 704
    assert body["actuals"]["height"] == 1024
    assert body["actuals"]["clip_skip"] == 2
    step_entry = next(c for c in body["comparisons"] if c["key"] == "GENERATION SETTINGS::Steps")
    assert step_entry["status"] in {"match", "out_of_range", "unknown"}
    assert "counts" in body


def test_workflow_rule_compare_lists_multiple_sampler_groups(client):
    test_client, main = client
    db = main.DATA_ROOT / "database" / "workbench.sqlite3"
    _seed_context_rules(db)

    workflow = {
        "5": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "sample_checkpoint.safetensors"}},
        "6": {"class_type": "KSampler", "inputs": {"steps": 20, "positive": ["1", 0], "negative": ["2", 0]}},
        "9": {"class_type": "KSampler", "inputs": {"steps": 30, "positive": ["1", 0], "negative": ["2", 0]}},
    }
    workflow_id = _import_sample(test_client, main, workflow)

    response = test_client.get(
        f"/api/workflows/{workflow_id}/rules/compare",
        headers={"Authorization": "Bearer test-session-token"},
    )
    assert response.status_code == 200
    body = response.json()
    actuals = body["actuals"]
    assert actuals["sampler_group_count"] == 2
    assert actuals["steps"] == 20
    assert [g["params"].get("steps") for g in actuals["sampler_groups"]] == [20, 30]


def test_workflow_rule_compare_unregistered_without_checkpoint(client):
    test_client, main = client
    db = main.DATA_ROOT / "database" / "workbench.sqlite3"
    _seed_context_rules(db)

    workflow = {"6": {"class_type": "KSampler", "inputs": {"steps": 20}}}
    workflow_id = _import_sample(test_client, main, workflow)

    response = test_client.get(
        f"/api/workflows/{workflow_id}/rules/compare",
        headers={"Authorization": "Bearer test-session-token"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unregistered"
    assert body["comparisons"] == []


def test_workflow_rule_prompt_unregistered_without_checkpoint(client):
    test_client, main = client
    db = main.DATA_ROOT / "database" / "workbench.sqlite3"
    _seed_context_rules(db)

    workflow = {"6": {"class_type": "KSampler", "inputs": {}}}
    workflow_id = _import_sample(test_client, main, workflow)

    response = test_client.get(
        f"/api/workflows/{workflow_id}/rules/prompt",
        headers={"Authorization": "Bearer test-session-token"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unregistered"
    assert body["fields"] == []


def test_workflow_rules_unregistered_without_checkpoint(client):
    test_client, main = client
    db = main.DATA_ROOT / "database" / "workbench.sqlite3"
    _seed_context_rules(db)

    workflow = {"6": {"class_type": "KSampler", "inputs": {}}}
    workflow_id = _import_sample(test_client, main, workflow)

    response = test_client.get(
        f"/api/workflows/{workflow_id}/rules",
        headers={"Authorization": "Bearer test-session-token"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unregistered"
    assert body["reason"] == "no_checkpoint_recognized"
    assert body["checkpoint"] is None
