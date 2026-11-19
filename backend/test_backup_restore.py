import io
import json
import zipfile
from pathlib import Path


def auth():
    return {"Authorization": "Bearer test-session-token"}


def _root(main) -> Path:
    return Path(main.DATA_ROOT)


def _build_archive(entries: dict[str, bytes], manifest_overrides=None) -> bytes:
    manifest = {
        "app": "ComfyUI-Prompt-Workbench",
        "version": "0.1.0-dev.5",
        "generated_at": "2026-11-19T00:00:00+00:00",
    }
    if manifest_overrides:
        manifest.update(manifest_overrides)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False))
        for rel, data in entries.items():
            zf.writestr(rel, data)
    return buf.getvalue()


def _restore(test_client, archive: bytes, overwrite: bool = False):
    url = "/api/backup/restore" + ("?overwrite=true" if overwrite else "")
    return test_client.post(url, headers=auth(), content=archive)


def test_restore_keeps_existing_and_adds_missing_by_default(client):
    test_client, main = client
    root = _root(main)
    test_client.get("/api/settings", headers=auth())

    current = root / "drafts" / "current.txt"
    current.parent.mkdir(parents=True, exist_ok=True)
    current.write_text("current", encoding="utf-8")

    archive = _build_archive(
        {
            "drafts/added.txt": b"added",
            "drafts/current.txt": b"restored",
        }
    )
    response = _restore(test_client, archive)
    assert response.status_code == 200, response.text
    report = response.json()

    # Missing file is written; existing file is kept by default.
    assert (root / "drafts" / "added.txt").read_text(encoding="utf-8") == "added"
    assert current.read_text(encoding="utf-8") == "current"
    assert "drafts/current.txt" in report["skipped_existing"]
    assert report["overwritten_count"] == 0

    # A pre-restore backup was written under backups/.
    pre_backup = root / report["pre_backup"]
    assert pre_backup.is_file()


def test_restore_overwrite_replaces_existing_files(client):
    test_client, main = client
    root = _root(main)
    test_client.get("/api/settings", headers=auth())

    current = root / "drafts" / "current.txt"
    current.parent.mkdir(parents=True, exist_ok=True)
    current.write_text("current", encoding="utf-8")

    archive = _build_archive({"drafts/current.txt": b"restored"})
    response = _restore(test_client, archive, overwrite=True)
    assert response.status_code == 200, response.text
    report = response.json()

    assert current.read_text(encoding="utf-8") == "restored"
    assert report["overwritten_count"] == 1
    assert report["skipped_existing"] == []


def test_restore_rejects_app_mismatch(client):
    test_client, _ = client
    test_client.get("/api/settings", headers=auth())
    archive = _build_archive(
        {"drafts/added.txt": b"x"},
        manifest_overrides={"app": "other-app"},
    )
    response = _restore(test_client, archive)
    assert response.status_code == 400


def test_restore_rejects_traversal_member(client):
    test_client, main = client
    root = _root(main)
    test_client.get("/api/settings", headers=auth())
    archive = _build_archive({"../evil.txt": b"x"})
    response = _restore(test_client, archive)
    assert response.status_code == 400
    assert not (root.parent / "evil.txt").exists()


def test_restore_rejects_corrupt_database_before_writing(client):
    test_client, main = client
    root = _root(main)
    test_client.get("/api/settings", headers=auth())

    marker = root / "drafts" / "marker.txt"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("keep", encoding="utf-8")

    archive = _build_archive(
        {
            "database/workbench.sqlite3": b"not-a-sqlite-database",
            "drafts/added.txt": b"added",
        }
    )
    response = _restore(test_client, archive)
    assert response.status_code == 400

    # Existing data stays intact; the bad archive was not partially applied.
    assert marker.read_text(encoding="utf-8") == "keep"
    assert not (root / "drafts" / "added.txt").exists()


def test_restore_rejects_non_zip(client):
    test_client, _ = client
    test_client.get("/api/settings", headers=auth())
    response = _restore(test_client, b"this is not a zip")
    assert response.status_code == 400
