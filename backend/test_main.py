import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKBENCH_SESSION_TOKEN", "test-session-token")
    monkeypatch.setenv("WORKBENCH_DATA_ROOT", str(tmp_path / "workbench-data"))

    # Import after setting environment variables so paths are isolated.
    sys.modules.pop("main", None)
    import main

    main.SESSION_TOKEN = "test-session-token"
    main.DATA_ROOT = tmp_path / "workbench-data"
    main.SETTINGS_FILE = main.DATA_ROOT / "settings.json"

    with TestClient(main.app) as test_client:
        yield test_client

    sys.modules.pop("main", None)

def auth():
    return {"Authorization": "Bearer test-session-token"}

def test_health_requires_token(client):
    assert client.get("/api/health").status_code == 401
    response = client.get("/api/health", headers=auth())
    assert response.status_code == 200
    assert response.json()["ok"] is True

def test_settings_create_managed_directories(client, tmp_path):
    response = client.get("/api/settings", headers=auth())
    assert response.status_code == 200

    storage = response.json()["storage"]
    assert Path(storage["database"]).is_dir()
    assert Path(storage["knowledge"]).is_dir()

def test_storage_validation(client, tmp_path):
    target = tmp_path / "new-folder"
    response = client.post(
        "/api/storage/validate",
        headers=auth(),
        json={"path": str(target), "create": True},
    )
    assert response.status_code == 200
    assert response.json()["exists"] is True
    assert response.json()["writable"] is True

def test_settings_reject_unknown_storage_key(client):
    response = client.post(
        "/api/settings",
        headers=auth(),
        json={"storage": {"unknown": "C:/bad"}},
    )
    assert response.status_code == 400

def test_services_offline_does_not_crash(client):
    response = client.get("/api/services/status", headers=auth())
    assert response.status_code == 200
    assert "ollama" in response.json()
    assert "comfyui" in response.json()
