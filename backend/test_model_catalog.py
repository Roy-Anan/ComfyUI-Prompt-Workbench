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


def test_catalog_annotates_clip_and_vae_against_configured_dir(tmp_path, monkeypatch):
    sys.modules.pop("model_catalog", None)
    import model_catalog

    clip_dir = tmp_path / "clip"
    clip_dir.mkdir()
    (clip_dir / "t5xxl.safetensors").write_bytes(b"clip")
    vae_dir = tmp_path / "vae"
    vae_dir.mkdir()

    object_info = {
        "CLIPLoader": {
            "input": {"required": {"clip_name": [["t5xxl.safetensors", "clip-missing.safetensors"], {}]}}
        },
        "VAELoader": {
            "input": {"required": {"vae_name": [["vae-missing.pt"], {}]}}
        },
    }
    monkeypatch.setattr(model_catalog, "_http_get_json", lambda url, timeout: object_info)

    report = model_catalog.fetch_catalog(
        "http://127.0.0.1:8188",
        clip_dir=str(clip_dir),
        vae_dir=str(vae_dir),
        timeout=1.0,
    )
    clips = {item["name"]: item["on_disk"] for item in report["clips"]}
    vaes = {item["name"]: item["on_disk"] for item in report["vaes"]}
    assert clips["t5xxl.safetensors"] is True
    assert clips["clip-missing.safetensors"] is False
    # Configured but empty directory -> VAE listed as not found, not unknown.
    assert vaes["vae-missing.pt"] is False

    # Unconfigured directories leave existence unknown (None).
    unknown = model_catalog.fetch_catalog("http://127.0.0.1:8188", timeout=1.0)
    assert unknown["clips"][0]["on_disk"] is None
    assert unknown["vaes"][0]["on_disk"] is None


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

    def fake_catalog(
        comfyui_url,
        checkpoint_dir="",
        lora_dir="",
        clip_dir="",
        vae_dir="",
        timeout=4.0,
    ):
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

    def fake_catalog(
        comfyui_url,
        checkpoint_dir="",
        lora_dir="",
        clip_dir="",
        vae_dir="",
        timeout=4.0,
    ):
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


def test_catalog_endpoint_attaches_identity_for_clip_vae_dirs(
    client, monkeypatch, tmp_path
):
    test_client, main = client
    clip_dir = tmp_path / "clip"
    vae_dir = tmp_path / "vae"
    clip_dir.mkdir()
    vae_dir.mkdir()
    (clip_dir / "clip-l.safetensors").write_bytes(b"clip-bytes")
    (vae_dir / "animevae.pt").write_bytes(b"vae-bytes")

    settings = test_client.get("/api/settings", headers=auth()).json()
    settings["storage"]["clip"] = str(clip_dir)
    settings["storage"]["vae"] = str(vae_dir)
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

    def fake_catalog(
        comfyui_url,
        checkpoint_dir="",
        lora_dir="",
        clip_dir="",
        vae_dir="",
        timeout=4.0,
    ):
        return {
            "online": True,
            "error": None,
            "checkpoints": [],
            "clips": [{"name": "clip-l.safetensors", "on_disk": True}],
            "vaes": [{"name": "animevae.pt", "on_disk": True}],
            "loras": [],
        }

    monkeypatch.setattr(main.model_catalog, "fetch_catalog", fake_catalog)

    body = test_client.get(
        "/api/models/catalog", headers=auth()
    ).json()
    clip_identity = body["clips"][0]["identity"]
    vae_identity = body["vaes"][0]["identity"]
    assert clip_identity["known"] is True
    assert clip_identity["on_disk"] is True
    assert clip_identity["size_bytes"] == len(b"clip-bytes")
    assert vae_identity["known"] is True
    assert vae_identity["on_disk"] is True
    assert vae_identity["size_bytes"] == len(b"vae-bytes")


def test_group_related_loras_reports_shared_triggers():
    import main

    loras = [
        {"name": "hero.safetensors"},
        {"name": "hero-v2.safetensors"},
        {"name": "other.safetensors"},
    ]
    meta = {
        "hero.safetensors": {"trigger_words": ["hero name", "dress"]},
        "hero-v2.safetensors": {"trigger_words": ["hero name", "solo"]},
        "other.safetensors": {"trigger_words": ["other"]},
    }
    related, triggers = main._group_related_loras(loras, meta)
    assert related["hero.safetensors"] == ["hero-v2.safetensors"]
    assert triggers["hero.safetensors"] == ["hero name"]
    assert triggers["hero-v2.safetensors"] == ["hero name"]
    assert related["other.safetensors"] == []
    assert triggers["other.safetensors"] == []


def test_group_compatible_loras_matches_shared_base():
    import main

    loras = [
        {"name": "hero.safetensors"},
        {"name": "hero-v2.safetensors"},
        {"name": "other.safetensors"},
        {"name": "nobase.safetensors"},
    ]
    meta = {
        "hero.safetensors": {"base_model": "Pony"},
        "hero-v2.safetensors": {"base_model": "pony"},
        "other.safetensors": {"base_model": "sd1.5"},
        "nobase.safetensors": {"base_model": ""},
    }
    compatible = main._group_compatible_loras(loras, meta)
    assert compatible["hero.safetensors"] == ["hero-v2.safetensors"]
    assert compatible["hero-v2.safetensors"] == ["hero.safetensors"]
    assert compatible["other.safetensors"] == []
    assert compatible["nobase.safetensors"] == []
