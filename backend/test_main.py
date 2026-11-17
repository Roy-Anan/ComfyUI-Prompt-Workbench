import sqlite3
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKBENCH_SESSION_TOKEN", "test-session-token")
    monkeypatch.setenv(
        "WORKBENCH_DATA_ROOT",
        str(tmp_path / "workbench-data"),
    )

    sys.modules.pop("main", None)
    import main

    main.SESSION_TOKEN = "test-session-token"
    main.DATA_ROOT = tmp_path / "workbench-data"
    main.SETTINGS_FILE = main.DATA_ROOT / "settings.json"

    with TestClient(main.app) as test_client:
        yield test_client, main

    sys.modules.pop("main", None)

def auth():
    return {"Authorization": "Bearer test-session-token"}

def test_health_requires_token(client):
    test_client, _ = client

    assert test_client.get("/api/health").status_code == 401

    wrong = test_client.get(
        "/api/health",
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert wrong.status_code == 401

    valid = test_client.get("/api/health", headers=auth())
    assert valid.status_code == 200
    assert valid.json()["ok"] is True

def test_cors_allows_vite_origin(client):
    test_client, _ = client

    response = test_client.options(
        "/api/health",
        headers={
            "Origin": "http://127.0.0.1:1420",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == (
        "http://127.0.0.1:1420"
    )

def test_cors_rejects_unknown_origin(client):
    test_client, _ = client

    response = test_client.options(
        "/api/health",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert "access-control-allow-origin" not in response.headers

def test_settings_create_managed_directories(client):
    test_client, _ = client

    response = test_client.get("/api/settings", headers=auth())
    assert response.status_code == 200

    storage = response.json()["storage"]

    keys = (
        "database", "knowledge", "prompts", "workflows",
        "drafts", "history", "cache", "logs",
        "backups", "exports",
    )

    for key in keys:
        assert Path(storage[key]).is_dir()

def test_sqlite_database_created(client):
    test_client, _ = client

    response = test_client.get("/api/settings", headers=auth())
    assert response.status_code == 200

    database_path = (
        Path(response.json()["storage"]["database"])
        / "workbench.sqlite3"
    )

    assert database_path.is_file()

    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }

        assert {"schema_version", "app_metadata"} <= tables

        version = connection.execute(
            "SELECT MAX(version) FROM schema_version"
        ).fetchone()[0]

        assert version == 1

def test_sqlite_reinitialization_preserves_version(client):
    test_client, main = client

    response = test_client.get("/api/settings", headers=auth())
    assert response.status_code == 200

    settings = response.json()
    database_path = (
        Path(settings["storage"]["database"])
        / "workbench.sqlite3"
    )

    main.initialize_database(settings)
    main.initialize_database(settings)

    with sqlite3.connect(database_path) as connection:
        version = connection.execute(
            "SELECT MAX(version) FROM schema_version"
        ).fetchone()[0]

    assert version == 1

def test_root_change_is_rejected(client):
    test_client, _ = client

    response = test_client.post(
        "/api/settings",
        headers=auth(),
        json={"storage": {"root": "D:/other-location"}},
    )

    assert response.status_code == 400
    assert "fixed" in response.json()["detail"]

def test_unknown_storage_key_is_rejected(client):
    test_client, _ = client

    response = test_client.post(
        "/api/settings",
        headers=auth(),
        json={"storage": {"unknown": "C:/bad"}},
    )

    assert response.status_code == 400

def test_external_model_paths_can_be_empty(client):
    test_client, _ = client

    response = test_client.post(
        "/api/settings",
        headers=auth(),
        json={
            "storage": {
                "checkpoint": "",
                "lora": "",
            }
        },
    )

    assert response.status_code == 200
    assert response.json()["storage"]["checkpoint"] == ""
    assert response.json()["storage"]["lora"] == ""

def test_external_model_path_must_exist_when_set(client, tmp_path):
    test_client, _ = client

    response = test_client.post(
        "/api/settings",
        headers=auth(),
        json={
            "storage": {
                "checkpoint": str(tmp_path / "missing-checkpoints")
            }
        },
    )

    assert response.status_code == 400

def test_storage_validation_can_create_directory(client, tmp_path):
    test_client, _ = client
    target = tmp_path / "new-managed-folder"

    response = test_client.post(
        "/api/storage/validate",
        headers=auth(),
        json={
            "path": str(target),
            "create": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["exists"] is True
    assert response.json()["is_directory"] is True
    assert response.json()["writable"] is True

def test_corrupt_settings_are_backed_up(client):
    test_client, main = client

    main.DATA_ROOT.mkdir(parents=True, exist_ok=True)
    main.SETTINGS_FILE.write_text(
        "{broken-json",
        encoding="utf-8",
    )

    response = test_client.get("/api/settings", headers=auth())

    assert response.status_code == 200
    assert response.json()["storage"]["root"] == str(main.DATA_ROOT)

    backups = list(
        main.DATA_ROOT.glob("settings.corrupt-*.json")
    )

    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "{broken-json"

def test_services_status_returns_when_services_offline(client):
    test_client, _ = client

    response = test_client.get(
        "/api/services/status",
        headers=auth(),
    )

    assert response.status_code == 200
    assert "ollama" in response.json()
    assert "comfyui" in response.json()
