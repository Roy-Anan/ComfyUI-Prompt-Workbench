import json
import sys

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
    sys.modules.pop("datadir", None)
    sys.modules.pop("model_catalog", None)
    import datadir
    import main

    main.BOOTSTRAP_TOKEN = "test-session-token"
    main.DATA_ROOT = datadir.default_data_root()
    main.SETTINGS_FILE = datadir.settings_path(main.DATA_ROOT)
    main.MIGRATION_REPORT = {}
    main.SESSION_TICKETS.clear()

    with TestClient(main.app) as test_client:
        yield test_client, main

    sys.modules.pop("main", None)
    sys.modules.pop("datadir", None)
    sys.modules.pop("model_catalog", None)


def auth():
    return {"Authorization": "Bearer test-session-token"}


def test_catalog_extracts_checkpoint_lora_and_vae_options():
    sys.modules.pop("model_catalog", None)
    import model_catalog

    object_info = {
        "CheckpointLoaderSimple": {
            "input": {
                "required": {
                    "ckpt_name": [
                        ["pony.safetensors", "realism.ckpt"],
                        {},
                    ]
                }
            }
        },
        "LoraLoader": {
            "input": {
                "required": {
                    "lora_name": [["lora-a.safetensors"], {}],
                    "strength_model": ["FLOAT", 0.7],
                }
            }
        },
        "VAELoader": {
            "input": {
                "required": {"vae_name": [["animevae.pt"], {}]}
            }
        },
    }

    checkpoints = model_catalog._extract_options(
        object_info, model_catalog.CHECKPOINT_WIDGETS
    )
    loras = model_catalog._extract_options(
        object_info, model_catalog.LORA_WIDGETS
    )
    vaes = model_catalog._extract_options(
        object_info, model_catalog.VAE_WIDGETS
    )

    assert checkpoints == ["pony.safetensors", "realism.ckpt"]
    assert loras == ["lora-a.safetensors"]
    assert vaes == ["animevae.pt"]


def test_catalog_marks_on_disk_only_when_directory_configured(tmp_path):
    sys.modules.pop("model_catalog", None)
    import model_catalog

    ckpt_dir = tmp_path / "ckpt"
    ckpt_dir.mkdir()
    (ckpt_dir / "pony.safetensors").write_bytes(b"x")

    annotated = model_catalog._annotate(
        ["pony.safetensors", "missing.safetensors"], str(ckpt_dir)
    )
    by_name = {item["name"]: item["on_disk"] for item in annotated}
    assert by_name["pony.safetensors"] is True
    assert by_name["missing.safetensors"] is False

    # No directory configured -> existence is unknown (None), not false.
    unknown = model_catalog._annotate(["pony.safetensors"], "")
    assert unknown[0]["on_disk"] is None


def test_catalog_unreachable_comfyui_reports_offline():
    sys.modules.pop("model_catalog", None)
    import model_catalog

    report = model_catalog.fetch_catalog(
        "http://127.0.0.1:1",
        checkpoint_dir="",
        lora_dir="",
        timeout=1.0,
    )
    assert report["online"] is False
    assert report["checkpoints"] == []
    assert report["clips"] == []
    assert report["vaes"] == []
    assert report["loras"] == []
    assert report["error"]


def test_catalog_endpoint_requires_session(client):
    test_client, _ = client
    missing = test_client.get("/api/models/catalog")
    assert missing.status_code == 401


def test_catalog_endpoint_returns_injected_catalog(client, monkeypatch):
    test_client, main = client

    def fake_catalog(comfyui_url, checkpoint_dir="", lora_dir="", timeout=4.0):
        return {
            "online": True,
            "error": None,
            "checkpoints": [{"name": "pony.safetensors", "on_disk": None}],
            "clips": [],
            "vaes": [{"name": "animevae.pt", "on_disk": None}],
            "loras": [{"name": "lora-a.safetensors", "on_disk": None}],
        }

    monkeypatch.setattr(main.model_catalog, "fetch_catalog", fake_catalog)

    response = test_client.get("/api/models/catalog", headers=auth())
    assert response.status_code == 200
    body = response.json()
    assert body["online"] is True
    assert body["checkpoints"][0]["name"] == "pony.safetensors"
    assert body["vaes"][0]["name"] == "animevae.pt"
    assert body["loras"][0]["name"] == "lora-a.safetensors"
    # No on-disk directory configured -> identity unknown.
    assert body["checkpoints"][0]["identity"] == {"known": False}


def test_catalog_endpoint_attaches_identity_for_configured_dir(
    client, monkeypatch, tmp_path
):
    test_client, main = client
    ckpt_dir = tmp_path / "ckpt"
    ckpt_dir.mkdir()
    (ckpt_dir / "pony.safetensors").write_bytes(b"weight")

    settings = test_client.get("/api/settings", headers=auth()).json()
    settings["storage"]["checkpoint"] = str(ckpt_dir)
    test_client.post(
        "/api/settings",
        headers=auth(),
        json={
            "storage": {
                k: v for k, v in settings["storage"].items() if k != "root"
            },
            "connections": settings["connections"],
        },
    )

    def fake_catalog(comfyui_url, checkpoint_dir="", lora_dir="", timeout=4.0):
        return {
            "online": True,
            "error": None,
            "checkpoints": [{"name": "pony.safetensors", "on_disk": True}],
            "clips": [],
            "vaes": [],
            "loras": [],
        }

    monkeypatch.setattr(main.model_catalog, "fetch_catalog", fake_catalog)

    body = test_client.get(
        "/api/models/catalog", headers=auth()
    ).json()
    identity = body["checkpoints"][0]["identity"]
    assert identity["known"] is True
    assert identity["on_disk"] is True
    assert identity["size_bytes"] == len(b"weight")
    assert identity["hashed"] is False
    assert identity["sha256"] is None
