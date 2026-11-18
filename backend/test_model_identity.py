import hashlib
import sqlite3
from pathlib import Path

import model_identity


def _db(tmp_path: Path) -> sqlite3.Connection:
    conn = model_identity.connect(tmp_path / "workbench.sqlite3")
    model_identity.ensure_schema(conn)
    return conn


def _write_model(directory: Path, name: str, content: bytes) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_bytes(content)
    return path


def test_index_directory_records_weight_metadata(tmp_path):
    conn = _db(tmp_path)
    ckpt = tmp_path / "ckpt"
    _write_model(ckpt, "pony.safetensors", b"pony-weight")

    records = model_identity.index_directory(conn, "checkpoint", str(ckpt))

    assert len(records) == 1
    record = records[0]
    assert record["relative_name"] == "pony.safetensors"
    assert record["size_bytes"] == len(b"pony-weight")
    assert record["sha256"] is None
    assert record["on_disk"] is True
    conn.close()


def test_index_ignores_non_weight_files(tmp_path):
    conn = _db(tmp_path)
    ckpt = tmp_path / "ckpt"
    _write_model(ckpt, "notes.txt", b"hello")
    _write_model(ckpt, "model.ckpt", b"ckpt-weight")

    records = model_identity.index_directory(conn, "checkpoint", str(ckpt))
    names = [r["relative_name"] for r in records]
    assert names == ["model.ckpt"]
    conn.close()


def test_changed_file_invalidates_cached_digest(tmp_path):
    conn = _db(tmp_path)
    lora = tmp_path / "lora"
    path = _write_model(lora, "a.safetensors", b"first")

    model_identity.index_directory(conn, "lora", str(lora))
    digested = model_identity.ensure_hash(conn, "lora", "a.safetensors")
    assert digested["sha256"] == hashlib.sha256(b"first").hexdigest()

    # Rewrite with different content; the cached digest must be dropped.
    path.write_bytes(b"second-content")
    model_identity.index_directory(conn, "lora", str(lora))
    stale = model_identity.lookup_name(conn, "lora", "a.safetensors")
    assert stale["sha256"] is None
    conn.close()


def test_ensure_hash_computes_and_caches(tmp_path):
    conn = _db(tmp_path)
    lora = tmp_path / "lora"
    _write_model(lora, "suyuexi.safetensors", b"lora-bytes")

    model_identity.index_directory(conn, "lora", str(lora))
    first = model_identity.ensure_hash(conn, "lora", "suyuexi.safetensors")
    expected = hashlib.sha256(b"lora-bytes").hexdigest()
    assert first["sha256"] == expected
    assert first["hashed_at"] is not None

    # Second call reuses the cached digest without recomputing.
    second = model_identity.ensure_hash(conn, "lora", "suyuexi.safetensors")
    assert second["sha256"] == expected
    conn.close()


def test_identity_summary_unknown_when_not_recorded(tmp_path):
    conn = _db(tmp_path)
    summary = model_identity.identity_summary(conn, "checkpoint", "ghost.safetensors")
    assert summary == {"known": False}
    conn.close()


def test_identity_summary_reports_cached_state(tmp_path):
    conn = _db(tmp_path)
    ckpt = tmp_path / "ckpt"
    _write_model(ckpt, "real.safetensors", b"weight")
    model_identity.index_directory(conn, "checkpoint", str(ckpt))

    summary = model_identity.identity_summary(conn, "checkpoint", "real.safetensors")
    assert summary["known"] is True
    assert summary["on_disk"] is True
    assert summary["hashed"] is False
    assert summary["sha256"] is None
    conn.close()


def test_identical_copies_share_one_identity(tmp_path):
    conn = _db(tmp_path)
    lora = tmp_path / "lora"
    payload = b"identical-weight-bytes"
    _write_model(lora, "copy-a.safetensors", payload)
    _write_model(lora, "copy-b.safetensors", payload)

    model_identity.index_directory(conn, "lora", str(lora))
    model_identity.ensure_hash(conn, "lora", "copy-a.safetensors")
    model_identity.ensure_hash(conn, "lora", "copy-b.safetensors")

    group_a = model_identity.identity_group(conn, "lora", "copy-a.safetensors")
    group_b = model_identity.identity_group(conn, "lora", "copy-b.safetensors")

    assert group_a["identity_key"] == group_b["identity_key"]
    assert group_a["digest"] == hashlib.sha256(payload).hexdigest()
    names = {copy["relative_name"] for copy in group_a["copies"]}
    assert names == {"copy-a.safetensors", "copy-b.safetensors"}

    summary = model_identity.identity_summary(conn, "lora", "copy-a.safetensors")
    assert summary["copy_count"] == 2
    conn.close()


def test_different_content_not_merged(tmp_path):
    conn = _db(tmp_path)
    lora = tmp_path / "lora"
    _write_model(lora, "alpha.safetensors", b"content-one")
    _write_model(lora, "beta.safetensors", b"content-two")

    model_identity.index_directory(conn, "lora", str(lora))
    model_identity.ensure_hash(conn, "lora", "alpha.safetensors")
    model_identity.ensure_hash(conn, "lora", "beta.safetensors")

    group_a = model_identity.identity_group(conn, "lora", "alpha.safetensors")
    group_b = model_identity.identity_group(conn, "lora", "beta.safetensors")
    assert group_a["identity_key"] != group_b["identity_key"]
    assert len(group_a["copies"]) == 1
    assert len(group_b["copies"]) == 1
    conn.close()


def test_unhashed_group_has_no_identity_key(tmp_path):
    conn = _db(tmp_path)
    ckpt = tmp_path / "ckpt"
    _write_model(ckpt, "ghost.safetensors", b"weight")
    model_identity.index_directory(conn, "checkpoint", str(ckpt))

    group = model_identity.identity_group(conn, "checkpoint", "ghost.safetensors")
    assert group["known"] is True
    assert group["identity_key"] is None
    assert group["copies"] == []
    conn.close()


def test_unknown_category_rejected(tmp_path):
    conn = _db(tmp_path)
    try:
        model_identity.index_directory(conn, "avatar", str(tmp_path))
        assert False, "expected ValueError"
    except ValueError:
        pass
    conn.close()
