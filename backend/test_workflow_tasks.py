import workflow_api

AUTH = {"Authorization": "Bearer test-session-token"}


def _api_workflow():
    return {
        "1": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "positive", "clip": ["5", 0]},
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "negative", "clip": ["5", 0]},
        },
        "5": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "x.safetensors"},
        },
    }


def _ui_workflow():
    return {"nodes": [{"id": 1, "type": "CLIPTextEncode"}], "links": []}


def _import(test_client, workflow):
    response = test_client.post(
        "/api/workflows/import",
        headers=AUTH,
        json={"filename": "sample.json", "workflow": workflow},
    )
    assert response.status_code == 200
    return response.json()["id"]


def _confirm(test_client, workflow_id):
    response = test_client.post(
        f"/api/workflows/{workflow_id}/confirm",
        headers=AUTH,
        json={"positive_node_ids": ["1"], "negative_node_ids": ["2"]},
    )
    assert response.status_code == 200


def _patch_gates(monkeypatch, online=True, loaded=None, submit=None):
    monkeypatch.setattr(
        workflow_api.comfy_client, "comfyui_online", lambda url: online
    )
    if loaded is None:
        loaded = {"online": True, "models": [], "error": None}
    monkeypatch.setattr(
        workflow_api.comfy_client, "loaded_ollama_models", lambda url: loaded
    )
    if submit is not None:
        monkeypatch.setattr(
            workflow_api.comfy_client, "submit_prompt", submit
        )


def test_submit_rejects_unconfirmed_workflow(client, monkeypatch):
    test_client, _ = client
    workflow_id = _import(test_client, _api_workflow())
    _patch_gates(monkeypatch)

    response = test_client.post(
        f"/api/workflows/{workflow_id}/tasks", headers=AUTH
    )
    assert response.status_code == 400


def test_submit_rejects_ui_format(client, monkeypatch):
    test_client, _ = client
    workflow_id = _import(test_client, _ui_workflow())
    _patch_gates(monkeypatch)

    response = test_client.post(
        f"/api/workflows/{workflow_id}/tasks", headers=AUTH
    )
    assert response.status_code == 400
    assert "API" in response.json()["detail"]


def test_submit_rejects_when_comfyui_offline(client, monkeypatch):
    test_client, _ = client
    workflow_id = _import(test_client, _api_workflow())
    _confirm(test_client, workflow_id)
    _patch_gates(monkeypatch, online=False)

    response = test_client.post(
        f"/api/workflows/{workflow_id}/tasks", headers=AUTH
    )
    assert response.status_code == 502
    assert response.json()["detail"]["online"] is False


def test_submit_rejects_when_ollama_offline(client, monkeypatch):
    test_client, _ = client
    workflow_id = _import(test_client, _api_workflow())
    _confirm(test_client, workflow_id)
    loaded = {"online": False, "models": [], "error": "connection refused"}
    _patch_gates(monkeypatch, loaded=loaded)

    response = test_client.post(
        f"/api/workflows/{workflow_id}/tasks", headers=AUTH
    )
    assert response.status_code == 502
    assert "卸载" in response.json()["detail"]["error"]


def test_submit_rejects_when_llm_still_loaded(client, monkeypatch):
    test_client, _ = client
    workflow_id = _import(test_client, _api_workflow())
    _confirm(test_client, workflow_id)
    loaded = {"online": True, "models": ["qwen3:latest"], "error": None}
    _patch_gates(monkeypatch, loaded=loaded)

    response = test_client.post(
        f"/api/workflows/{workflow_id}/tasks", headers=AUTH
    )
    assert response.status_code == 409
    assert response.json()["detail"]["loaded"] == ["qwen3:latest"]


def test_submit_records_task_when_gates_pass(client, monkeypatch):
    test_client, _ = client
    workflow_id = _import(test_client, _api_workflow())
    _confirm(test_client, workflow_id)

    def fake_submit(url, prompt_api, client_id, timeout=10.0):
        return {
            "ok": True,
            "prompt_id": "prompt-1",
            "node_errors": {},
            "error": None,
        }

    _patch_gates(monkeypatch, submit=fake_submit)

    response = test_client.post(
        f"/api/workflows/{workflow_id}/tasks", headers=AUTH
    )
    assert response.status_code == 200
    record = response.json()
    assert record["prompt_id"] == "prompt-1"
    assert record["workflow_id"] == workflow_id
    assert record["status"] == "submitted"

    listed = test_client.get(
        f"/api/workflows/{workflow_id}/tasks", headers=AUTH
    ).json()
    assert [item["prompt_id"] for item in listed["items"]] == ["prompt-1"]


def test_submit_failure_records_no_task(client, monkeypatch):
    test_client, _ = client
    workflow_id = _import(test_client, _api_workflow())
    _confirm(test_client, workflow_id)

    def fake_submit(url, prompt_api, client_id, timeout=10.0):
        return {
            "ok": False,
            "prompt_id": None,
            "node_errors": {"3": {"errors": ["missing model"]}},
            "error": "ComfyUI 报告节点错误",
        }

    _patch_gates(monkeypatch, submit=fake_submit)

    response = test_client.post(
        f"/api/workflows/{workflow_id}/tasks", headers=AUTH
    )
    assert response.status_code == 502
    assert response.json()["detail"]["node_errors"]

    listed = test_client.get(
        f"/api/workflows/{workflow_id}/tasks", headers=AUTH
    ).json()
    assert listed["items"] == []


def test_list_tasks_returns_404_for_unknown_workflow(client):
    test_client, _ = client
    response = test_client.get(
        "/api/workflows/00000000-0000-4000-8000-000000000000/tasks",
        headers=AUTH,
    )
    assert response.status_code == 404
