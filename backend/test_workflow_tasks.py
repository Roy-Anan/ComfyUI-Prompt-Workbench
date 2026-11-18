import llm_client
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


def _submit_one(test_client, monkeypatch, prompt_id="prompt-1"):
    workflow_id = _import(test_client, _api_workflow())
    _confirm(test_client, workflow_id)

    def fake_submit(url, prompt_api, client_id, timeout=10.0):
        return {
            "ok": True,
            "prompt_id": prompt_id,
            "node_errors": {},
            "error": None,
        }

    _patch_gates(monkeypatch, submit=fake_submit)
    response = test_client.post(
        f"/api/workflows/{workflow_id}/tasks", headers=AUTH
    )
    assert response.status_code == 200
    return workflow_id


def test_refresh_maps_history_success(client, monkeypatch):
    test_client, _ = client
    workflow_id = _submit_one(test_client, monkeypatch)

    monkeypatch.setattr(
        workflow_api.comfy_client,
        "fetch_task_states",
        lambda url: {
            "online": True,
            "error": None,
            "running": [],
            "pending": [],
            "history": {
                "prompt-1": {
                    "status_str": "success",
                    "completed": True,
                    "outputs": {"9": [{"filename": "a.png"}]},
                }
            },
        },
    )

    body = test_client.get(
        f"/api/workflows/{workflow_id}/tasks?refresh=true", headers=AUTH
    ).json()
    record = body["items"][0]
    assert record["status"] == "succeeded"
    assert record["outputs"] == {"9": [{"filename": "a.png"}]}
    assert body["sync_error"] is None


def test_refresh_maps_queue_running(client, monkeypatch):
    test_client, _ = client
    workflow_id = _submit_one(test_client, monkeypatch)

    monkeypatch.setattr(
        workflow_api.comfy_client,
        "fetch_task_states",
        lambda url: {
            "online": True,
            "error": None,
            "running": ["prompt-1"],
            "pending": [],
            "history": {},
        },
    )

    body = test_client.get(
        f"/api/workflows/{workflow_id}/tasks?refresh=true", headers=AUTH
    ).json()
    assert body["items"][0]["status"] == "running"


def test_refresh_marks_unknown_when_absent_from_queue_and_history(client, monkeypatch):
    test_client, _ = client
    workflow_id = _submit_one(test_client, monkeypatch)

    monkeypatch.setattr(
        workflow_api.comfy_client,
        "fetch_task_states",
        lambda url: {
            "online": True,
            "error": None,
            "running": [],
            "pending": [],
            "history": {},
        },
    )

    body = test_client.get(
        f"/api/workflows/{workflow_id}/tasks?refresh=true", headers=AUTH
    ).json()
    record = body["items"][0]
    assert record["status"] == "unknown"
    assert record["last_error"]


def test_refresh_offline_keeps_local_status(client, monkeypatch):
    test_client, _ = client
    workflow_id = _submit_one(test_client, monkeypatch)

    monkeypatch.setattr(
        workflow_api.comfy_client,
        "fetch_task_states",
        lambda url: {
            "online": False,
            "error": "connection refused",
            "running": [],
            "pending": [],
            "history": {},
        },
    )

    body = test_client.get(
        f"/api/workflows/{workflow_id}/tasks?refresh=true", headers=AUTH
    ).json()
    assert body["items"][0]["status"] == "submitted"
    assert body["sync_error"] == "connection refused"


def test_classify_history_status_is_conservative():
    classify = workflow_api.comfy_tasks.classify_history_status
    assert classify("success", True) == "succeeded"
    assert classify("success", None) == "succeeded"
    assert classify("error", False) == "failed"
    assert classify("interrupted", None) == "interrupted"
    assert classify(None, None) == "unknown"
    assert classify("running", None) == "unknown"


def _set_status(main, prompt_id: str, status: str) -> None:
    db = main.DATA_ROOT / "database" / "workbench.sqlite3"
    with workflow_api.model_identity.connect(db) as connection:
        workflow_api.comfy_tasks.ensure_schema(connection)
        workflow_api.comfy_tasks.update_status(connection, prompt_id, status)


def test_cancel_pending_task_dequeues_and_marks_interrupted(client, monkeypatch):
    test_client, main = client
    workflow_id = _submit_one(test_client, monkeypatch)
    dequeued: list[str] = []
    monkeypatch.setattr(
        workflow_api.comfy_client,
        "cancel_pending",
        lambda url, pid: dequeued.append(pid) or {"ok": True, "error": None},
    )
    monkeypatch.setattr(
        workflow_api.comfy_client,
        "interrupt_running",
        lambda url, pid: {"ok": False, "error": "should not call"},
    )

    response = test_client.post(
        f"/api/workflows/{workflow_id}/tasks/prompt-1/cancel", headers=AUTH
    )
    assert response.status_code == 200
    assert dequeued == ["prompt-1"]
    assert response.json()["status"] == "interrupted"


def test_interrupt_running_task_targets_prompt(client, monkeypatch):
    test_client, main = client
    workflow_id = _submit_one(test_client, monkeypatch)
    _set_status(main, "prompt-1", "running")
    interrupted: list[str] = []
    monkeypatch.setattr(
        workflow_api.comfy_client,
        "interrupt_running",
        lambda url, pid: interrupted.append(pid) or {"ok": True, "error": None},
    )
    monkeypatch.setattr(
        workflow_api.comfy_client,
        "cancel_pending",
        lambda url, pid: {"ok": False, "error": "should not call"},
    )

    response = test_client.post(
        f"/api/workflows/{workflow_id}/tasks/prompt-1/cancel", headers=AUTH
    )
    assert response.status_code == 200
    assert interrupted == ["prompt-1"]
    assert response.json()["status"] == "interrupted"


def test_cancel_refuses_terminal_task(client, monkeypatch):
    test_client, main = client
    workflow_id = _submit_one(test_client, monkeypatch)
    _set_status(main, "prompt-1", "succeeded")

    response = test_client.post(
        f"/api/workflows/{workflow_id}/tasks/prompt-1/cancel", headers=AUTH
    )
    assert response.status_code == 409


def test_cancel_refuses_unknown_task(client, monkeypatch):
    test_client, main = client
    workflow_id = _submit_one(test_client, monkeypatch)
    _set_status(main, "prompt-1", "unknown")

    response = test_client.post(
        f"/api/workflows/{workflow_id}/tasks/prompt-1/cancel", headers=AUTH
    )
    assert response.status_code == 409


def test_cancel_offline_leaves_local_status(client, monkeypatch):
    test_client, main = client
    workflow_id = _submit_one(test_client, monkeypatch)
    monkeypatch.setattr(
        workflow_api.comfy_client, "comfyui_online", lambda url: False
    )

    response = test_client.post(
        f"/api/workflows/{workflow_id}/tasks/prompt-1/cancel", headers=AUTH
    )
    assert response.status_code == 502
    listed = test_client.get(
        f"/api/workflows/{workflow_id}/tasks", headers=AUTH
    ).json()
    assert listed["items"][0]["status"] == "submitted"


def test_cancel_unknown_prompt_returns_404(client, monkeypatch):
    test_client, _ = client
    workflow_id = _submit_one(test_client, monkeypatch)

    response = test_client.post(
        f"/api/workflows/{workflow_id}/tasks/does-not-exist/cancel", headers=AUTH
    )
    assert response.status_code == 404


def _fake_chat_record(called: dict):
    def fake_chat(url, model, messages, timeout=30.0):
        called["chat"] = True
        return {"ok": True, "content": "candidate", "model": model, "error": None}

    return fake_chat


def test_retry_resubmits_failed_task(client, monkeypatch):
    test_client, main = client
    workflow_id = _submit_one(test_client, monkeypatch, prompt_id="prompt-1")
    _set_status(main, "prompt-1", "failed")

    calls: list[str] = []

    def fake_submit(url, prompt_api, client_id, timeout=10.0):
        pid = "prompt-2" if not calls else "prompt-x"
        calls.append(pid)
        return {"ok": True, "prompt_id": pid, "node_errors": {}, "error": None}

    monkeypatch.setattr(workflow_api.comfy_client, "submit_prompt", fake_submit)

    response = test_client.post(
        f"/api/workflows/{workflow_id}/tasks/prompt-1/retry", headers=AUTH
    )
    assert response.status_code == 200
    new_record = response.json()
    assert new_record["prompt_id"] == "prompt-2"
    assert new_record["status"] == "submitted"

    listed = test_client.get(
        f"/api/workflows/{workflow_id}/tasks", headers=AUTH
    ).json()["items"]
    by_id = {item["prompt_id"]: item for item in listed}
    assert set(by_id) == {"prompt-1", "prompt-2"}
    assert by_id["prompt-1"]["status"] == "failed"


def test_retry_refuses_succeeded_task(client, monkeypatch):
    test_client, main = client
    workflow_id = _submit_one(test_client, monkeypatch)
    _set_status(main, "prompt-1", "succeeded")

    submit_called = {"n": 0}
    monkeypatch.setattr(
        workflow_api.comfy_client,
        "submit_prompt",
        lambda *args, **kwargs: submit_called.__setitem__("n", 1)
        or {"ok": False, "prompt_id": None, "node_errors": {}, "error": "x"},
    )

    response = test_client.post(
        f"/api/workflows/{workflow_id}/tasks/prompt-1/retry", headers=AUTH
    )
    assert response.status_code == 409
    assert submit_called["n"] == 0


def test_retry_refuses_unknown_task(client, monkeypatch):
    test_client, main = client
    workflow_id = _submit_one(test_client, monkeypatch)
    _set_status(main, "prompt-1", "unknown")

    response = test_client.post(
        f"/api/workflows/{workflow_id}/tasks/prompt-1/retry", headers=AUTH
    )
    assert response.status_code == 409


def test_retry_unknown_prompt_returns_404(client, monkeypatch):
    test_client, _ = client
    workflow_id = _submit_one(test_client, monkeypatch)

    response = test_client.post(
        f"/api/workflows/{workflow_id}/tasks/does-not-exist/retry", headers=AUTH
    )
    assert response.status_code == 404


def test_versions_empty_for_fresh_workflow(client):
    test_client, _ = client
    workflow_id = _import(test_client, _api_workflow())

    response = test_client.get(
        f"/api/workflows/{workflow_id}/versions", headers=AUTH
    )
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_versions_unknown_workflow_returns_404(client):
    test_client, _ = client
    response = test_client.get(
        "/api/workflows/00000000-0000-4000-8000-000000000000/versions",
        headers=AUTH,
    )
    assert response.status_code == 404


def test_candidate_blocked_when_comfyui_queue_active(client, monkeypatch):
    test_client, _ = client
    workflow_id = _import(test_client, _api_workflow())
    monkeypatch.setattr(
        workflow_api.comfy_client,
        "queue_has_active_task",
        lambda url: {"online": True, "active": True, "error": None},
    )
    called: dict = {}
    monkeypatch.setattr(llm_client, "chat", _fake_chat_record(called))

    response = test_client.post(
        f"/api/workflows/{workflow_id}/prompt/candidates",
        headers=AUTH,
        json={"model": "qwen3:latest"},
    )
    assert response.status_code == 409
    assert called.get("chat") is not True


def test_candidate_allowed_when_queue_idle(client, monkeypatch):
    test_client, _ = client
    workflow_id = _import(test_client, _api_workflow())
    monkeypatch.setattr(
        workflow_api.comfy_client,
        "queue_has_active_task",
        lambda url: {"online": True, "active": False, "error": None},
    )
    called: dict = {}
    monkeypatch.setattr(llm_client, "chat", _fake_chat_record(called))

    response = test_client.post(
        f"/api/workflows/{workflow_id}/prompt/candidates",
        headers=AUTH,
        json={"model": "qwen3:latest"},
    )
    assert response.status_code == 200
    assert called.get("chat") is True


def test_candidate_allowed_when_comfyui_offline(client, monkeypatch):
    test_client, _ = client
    workflow_id = _import(test_client, _api_workflow())
    monkeypatch.setattr(
        workflow_api.comfy_client,
        "queue_has_active_task",
        lambda url: {"online": False, "active": False, "error": "refused"},
    )
    called: dict = {}
    monkeypatch.setattr(llm_client, "chat", _fake_chat_record(called))

    response = test_client.post(
        f"/api/workflows/{workflow_id}/prompt/candidates",
        headers=AUTH,
        json={"model": "qwen3:latest"},
    )
    assert response.status_code == 200
    assert called.get("chat") is True
