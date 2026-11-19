import comfy_client


def test_stop_ollama_model_posts_stop(monkeypatch):
    calls = []

    def fake_post(url, payload, timeout):
        calls.append((url, payload))
        return 200, {}, None

    monkeypatch.setattr(comfy_client, "_post_json", fake_post)
    result = comfy_client.stop_ollama_model("http://127.0.0.1:11434", "m:v1")

    assert result["ok"] is True
    assert calls[0][0].endswith("/api/stop")
    assert calls[0][1] == {"model": "m:v1"}


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


def test_release_resources_unloads_loaded_llm_and_frees_comfy(monkeypatch):
    monkeypatch.setattr(
        comfy_client,
        "loaded_ollama_models",
        lambda url, timeout=2.5: {
            "online": True,
            "models": ["a:v1", "b:v2"],
            "error": None,
        },
    )
    stops = []

    def fake_stop(url, model, timeout=5.0):
        stops.append(model)
        return {"ok": True, "model": model, "error": None}

    monkeypatch.setattr(comfy_client, "stop_ollama_model", fake_stop)
    monkeypatch.setattr(
        comfy_client,
        "free_comfyui_models",
        lambda url, timeout=5.0: {"ok": True, "error": None},
    )

    result = comfy_client.release_resources(
        "http://127.0.0.1:11434", "http://127.0.0.1:8188"
    )

    assert stops == ["a:v1", "b:v2"]
    assert result["ollama_stopped"] == ["a:v1", "b:v2"]
    assert result["ollama_errors"] == []
    assert result["comfyui_freed"] is True
    assert result["comfyui_error"] is None


def test_release_resources_collects_errors_without_raising(monkeypatch):
    monkeypatch.setattr(
        comfy_client,
        "loaded_ollama_models",
        lambda url, timeout=2.5: {
            "online": True,
            "models": ["a:v1"],
            "error": None,
        },
    )

    def fake_stop(url, model, timeout=5.0):
        return {"ok": False, "model": model, "error": "boom"}

    monkeypatch.setattr(comfy_client, "stop_ollama_model", fake_stop)
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
    assert result["comfyui_freed"] is False
    assert result["comfyui_error"] == "offline"
