import io
import json
import sqlite3
import zipfile
from pathlib import Path


def auth():
    return {"Authorization": "Bearer test-session-token"}


def _root(main) -> Path:
    return Path(main.DATA_ROOT)


def _seed_files(root: Path) -> None:
    """Write one marker file into each included and excluded domain."""
    markers = {
        "workflows": "wf-marker.json",
        "knowledge": "arch.txt",
        "prompts": "template.txt",
        "drafts": "draft.txt",
        "history": "history-index.txt",
        "cache": "cache.tmp",
        "logs": "runtime.log",
        "backups": "prior-backup.json",
        "exports": "prior-export.json",
    }
    for dir_name, name in markers.items():
        target = root / dir_name / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"{dir_name}-marker", encoding="utf-8")

    # Corrupt-settings sidecar must be excluded alongside prior backups.
    (root / "settings" / "settings.corrupt-20260101-000000-abc.json").write_text(
        "{}", encoding="utf-8"
    )


def test_backup_archive_includes_persistent_domains(client, tmp_path):
    test_client, main = client
    root = _root(main)

    # Initialize the managed root and database schema.
    init = test_client.get("/api/settings", headers=auth())
    assert init.status_code == 200

    _seed_files(root)

    response = test_client.get("/api/backup/export", headers=auth())
    assert response.status_code == 200
    assert "zip" in response.headers["content-type"]

    archive = zipfile.ZipFile(io.BytesIO(response.content))
    names = set(archive.namelist())

    # Included persistent domains and the settings file are archived.
    for rel in (
        "settings/settings.json",
        "database/workbench.sqlite3",
        "workflows/wf-marker.json",
        "knowledge/arch.txt",
        "prompts/template.txt",
        "drafts/draft.txt",
        "history/history-index.txt",
        "manifest.json",
    ):
        assert rel in names, f"missing {rel}"

    # Excluded rebuildable / self-referential domains and corrupt sidecars.
    for rel in (
        "cache/cache.tmp",
        "logs/runtime.log",
        "backups/prior-backup.json",
        "exports/prior-export.json",
        "settings/settings.corrupt-20260101-000000-abc.json",
    ):
        assert rel not in names, f"excluded {rel} was archived"

    manifest = json.loads(archive.read("manifest.json"))
    assert manifest["database"]["integrity"] == "ok"
    assert manifest["database"]["included"] is True
    assert manifest["settings"]["included"] is True
    for dir_name in ("workflows", "knowledge", "prompts", "drafts", "history"):
        assert manifest["domains"][dir_name]["files"] == 1

    # The archived database is a real openable SQLite file.
    db_bytes = archive.read("database/workbench.sqlite3")
    tmp_db = tmp_path / "restored.sqlite3"
    tmp_db.write_bytes(db_bytes)
    check = sqlite3.connect(str(tmp_db))
    tables = {
        row[0]
        for row in check.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    check.close()
    assert "workbench_rule" in tables


def test_backup_records_external_paths_without_copying(client, tmp_path):
    test_client, main = client
    root = _root(main)
    init = test_client.get("/api/settings", headers=auth())
    assert init.status_code == 200

    external_output = tmp_path / "comfy-output"
    external_output.mkdir()
    (external_output / "image.png").write_bytes(b"\x89PNG\r\n")

    settings = init.json()
    settings["storage"]["output"] = str(external_output)
    saved = test_client.post(
        "/api/settings",
        headers={**auth(), "X-Workbench-CSRF": ""},
        json={"storage": {"output": str(external_output)}, "connections": {}},
    )
    # Bearer session is exempt from the CSRF header check; save should accept.
    assert saved.status_code == 200, saved.text

    response = test_client.get("/api/backup/export", headers=auth())
    assert response.status_code == 200
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    manifest = json.loads(archive.read("manifest.json"))

    ext = manifest["external_directories"]["output"]
    assert ext["configured"] == str(external_output)
    assert ext["exists"] is True

    # The original image is never copied into the backup.
    assert not any("image.png" in name for name in archive.namelist())
