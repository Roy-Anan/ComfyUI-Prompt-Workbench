import comfy_client


def test_unload_ollama_model_posts_generate_keep_alive_zero(monkeypatch):
    calls = []

    def fake_post(url, payload, timeout):
        calls.append((url, payload))
        return 200, {}, None

    monkeypatch.setattr(comfy_client, "_post_json", fake_post)
    result = comfy_client.unload_ollama_model("http://127.0.0.1:11434", "m:v1")

    assert result["ok"] is True
    assert calls[0][0].endswith("/api/generate")
    assert calls[0][1]["model"] == "m:v1"
    assert calls[0][1]["prompt"] == ""
    assert calls[0][1]["keep_alive"] == 0
    assert calls[0][1]["stream"] is False


def test_free_comfyui_models_posts_free(monkeypatch):
    calls = []

    def fake_post(url, payload, timeout):
        calls.append((url, payload))
        return 200, {}, None

    monkeypatch.setattr(comfy_client, "_post_json", fake_post)
    result = comfy_client.free_comfyui_models("http://127.0.0.1:8188")

    assert result["ok"] is True
    assert calls[0][0].endswith("/free")
    assert calls[0][1] == {"unload_models": True, "free_memory": True}


def test_release_unloads_loaded_llm_and_reports_freed(monkeypatch):
    probe = [
        {"online": True, "reachable": True, "models": ["a:v1", "b:v2"], "error": None},
        {"online": True, "reachable": True, "models": [], "error": None},
    ]
    monkeypatch.setattr(
        comfy_client, "loaded_ollama_models", lambda url, timeout=2.5: probe.pop(0)
    )
    stopped = []

    def fake_unload(url, model, timeout=5.0):
        stopped.append(model)
        return {"ok": True, "model": model, "error": None}

    monkeypatch.setattr(comfy_client, "unload_ollama_model", fake_unload)
    monkeypatch.setattr(
        comfy_client,
        "free_comfyui_models",
        lambda url, timeout=5.0: {"ok": True, "error": None},
    )

    result = comfy_client.release_resources(
        "http://127.0.0.1:11434", "http://127.0.0.1:8188"
    )

    assert stopped == ["a:v1", "b:v2"]
    assert result["ollama_stopped"] == ["a:v1", "b:v2"]
    assert result["ollama_errors"] == []
    assert result["ollama_still_resident"] == []
    assert result["comfyui_freed"] is True
    assert result["comfyui_error"] is None


def test_release_reports_models_still_resident_after_unload(monkeypatch):
    probe = [
        {"online": True, "reachable": True, "models": ["a:v1"], "error": None},
        {"online": True, "reachable": True, "models": ["a:v1"], "error": None},
    ]
    monkeypatch.setattr(
        comfy_client, "loaded_ollama_models", lambda url, timeout=2.5: probe.pop(0)
    )
    monkeypatch.setattr(
        comfy_client,
        "unload_ollama_model",
        lambda url, model, timeout=5.0: {"ok": True, "model": model, "error": None},
    )
    monkeypatch.setattr(
        comfy_client,
        "free_comfyui_models",
        lambda url, timeout=5.0: {"ok": True, "error": None},
    )

    result = comfy_client.release_resources(
        "http://127.0.0.1:11434", "http://127.0.0.1:8188"
    )

    assert result["ollama_stopped"] == ["a:v1"]
    assert result["ollama_still_resident"] == ["a:v1"]


def test_release_collects_errors_without_raising(monkeypatch):
    probe = [
        {"online": True, "reachable": True, "models": ["a:v1"], "error": None},
        {"online": True, "reachable": True, "models": ["a:v1"], "error": None},
    ]
    monkeypatch.setattr(
        comfy_client, "loaded_ollama_models", lambda url, timeout=2.5: probe.pop(0)
    )

    def fake_unload(url, model, timeout=5.0):
        return {"ok": False, "model": model, "error": "boom"}

    monkeypatch.setattr(comfy_client, "unload_ollama_model", fake_unload)
    monkeypatch.setattr(
        comfy_client,
        "free_comfyui_models",
        lambda url, timeout=5.0: {"ok": False, "error": "offline"},
    )

    result = comfy_client.release_resources(
        "http://127.0.0.1:11434", "http://127.0.0.1:8188"
    )

    assert result["ollama_stopped"] == []
    assert result["ollama_errors"] == ["a:v1: boom"]
    assert result["ollama_still_resident"] == ["a:v1"]
    assert result["comfyui_freed"] is False
    assert result["comfyui_error"] == "offline"


def test_release_unreachable_ollama_skips_unload(monkeypatch):
    monkeypatch.setattr(
        comfy_client,
        "loaded_ollama_models",
        lambda url, timeout=2.5: {
            "online": False,
            "reachable": False,
            "models": [],
            "error": "connection refused",
        },
    )
    called = []
    monkeypatch.setattr(
        comfy_client,
        "unload_ollama_model",
        lambda url, model, timeout=5.0: called.append(model),
    )
    monkeypatch.setattr(
        comfy_client,
        "free_comfyui_models",
        lambda url, timeout=5.0: {"ok": True, "error": None},
    )

    result = comfy_client.release_resources(
        "http://127.0.0.1:11434", "http://127.0.0.1:8188"
    )

    assert called == []
    assert result["ollama_reachable"] is False
    assert result["ollama_stopped"] == []
    assert result["ollama_still_resident"] == []
