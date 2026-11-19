import textwrap

import profile_source


def _seed_profiles(root, monkeypatch):
    monkeypatch.setenv("WORKBENCH_PROFILES_DIR", str(root))
    (root / "Alpha.txt").write_text(
        textwrap.dedent(
            """\
            [IDENTITY]
            Display Name: Alpha Model
            Exact Checkpoint Filename: alpha.safetensors

            [ARCHITECTURE]
            Base Architecture: [已核实] SDXL 1.0
            VAE: 未给出

            [GENERATION SETTINGS]
            Steps: [作者推荐] 20
            """
        ),
        encoding="utf-8",
    )
    (root / "Beta.txt").write_text(
        "[IDENTITY]\nDisplay Name: Beta\nExact Checkpoint Filename: beta.safetensors\n",
        encoding="utf-8",
    )


def test_list_profiles_summaries(client, tmp_path, monkeypatch):
    test_client, main = client
    _seed_profiles(tmp_path, monkeypatch)
    headers = {"Authorization": "Bearer test-session-token"}

    response = test_client.get("/api/profiles", headers=headers)
    assert response.status_code == 200
    items = {item["file"]: item for item in response.json()["items"]}

    assert set(items) == {"Alpha.txt", "Beta.txt"}
    alpha = items["Alpha.txt"]
    assert alpha["filename"] == "alpha.safetensors"
    assert alpha["architecture"] == "SDXL 1.0"
    assert alpha["candidates"] == 2  # Base Architecture + Steps; VAE is missing.
    assert "VAE" in [field.split("::")[1] for field in alpha["unknown_fields"]]
    assert alpha["error"] is None


def test_preview_profile_candidates(client, tmp_path, monkeypatch):
    test_client, _ = client
    _seed_profiles(tmp_path, monkeypatch)
    headers = {"Authorization": "Bearer test-session-token"}

    response = test_client.get("/api/profiles/Alpha.txt", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "alpha.safetensors"
    assert body["display_name"] == "Alpha Model"

    records = body["candidates"]
    assert len(records) == 3
    steps = next(r for r in records if r["rule_key"] == "GENERATION SETTINGS::Steps")
    assert steps["level"] == "checkpoint"
    assert steps["scope_key"] == "alpha.safetensors"
    assert steps["value"] == "20"
    assert steps["provenance"] == "author"
    assert steps["confidence"] == "authoritative"
    identity = next(r for r in records if r["rule_key"] == "IDENTITY::Base Architecture")
    assert identity["level"] == "checkpoint"
    assert identity["scope_key"] == "alpha.safetensors"
    assert identity["value"] == "SDXL 1.0"
    # Preview must not have persisted anything.
    stored = test_client.get("/api/rules", headers=headers)
    assert stored.json()["items"] == []


def test_preview_flags_new_candidates_when_store_empty(client, tmp_path, monkeypatch):
    test_client, _ = client
    _seed_profiles(tmp_path, monkeypatch)
    headers = {"Authorization": "Bearer test-session-token"}

    response = test_client.get("/api/profiles/Alpha.txt", headers=headers)
    records = response.json()["candidates"]
    assert {r["diff"] for r in records} == {"new"}
    assert all("stored_value" not in r for r in records)


def test_preview_flags_same_and_override_after_import(client, tmp_path, monkeypatch):
    test_client, _ = client
    _seed_profiles(tmp_path, monkeypatch)
    headers = {"Authorization": "Bearer test-session-token"}

    imported = test_client.post(
        "/api/profiles/import", headers=headers, json={"file_name": "Alpha.txt"}
    )
    assert imported.status_code == 200

    after_import = test_client.get("/api/profiles/Alpha.txt", headers=headers).json()
    records = {r["rule_key"]: r for r in after_import["candidates"]}
    assert {r["diff"] for r in records.values()} == {"same"}

    changed = test_client.post(
        "/api/rules",
        headers=headers,
        json={
            "level": "checkpoint",
            "scope_key": "alpha.safetensors",
            "rule_key": "GENERATION SETTINGS::Steps",
            "value": "30",
            "provenance": "unverified",
            "confidence": "unverified",
        },
    )
    assert changed.status_code == 200

    after_change = test_client.get("/api/profiles/Alpha.txt", headers=headers).json()
    updated = {r["rule_key"]: r for r in after_change["candidates"]}
    assert updated["GENERATION SETTINGS::Steps"]["diff"] == "override"
    assert updated["GENERATION SETTINGS::Steps"]["stored_value"] == "30"
    others = [
        r for key, r in updated.items() if key != "GENERATION SETTINGS::Steps"
    ]
    assert {r["diff"] for r in others} == {"same"}


def test_preview_profile_unknown_file_returns_404(client, tmp_path, monkeypatch):
    test_client, _ = client
    _seed_profiles(tmp_path, monkeypatch)
    headers = {"Authorization": "Bearer test-session-token"}

    response = test_client.get("/api/profiles/Missing.txt", headers=headers)
    assert response.status_code == 404


def test_import_profile_persists_candidates(client, tmp_path, monkeypatch):
    test_client, _ = client
    _seed_profiles(tmp_path, monkeypatch)
    headers = {"Authorization": "Bearer test-session-token"}

    imported = test_client.post(
        "/api/profiles/import", headers=headers, json={"file_name": "Alpha.txt"}
    )
    assert imported.status_code == 200
    report = imported.json()
    assert report["filename"] == "alpha.safetensors"
    assert report["imported"] == 3
    assert report["rejected"] == []

    stored = test_client.get(
        "/api/rules?level=checkpoint&scope_key=alpha.safetensors", headers=headers
    )
    items = stored.json()["items"]
    keys = {item["rule_key"] for item in items}
    assert "GENERATION SETTINGS::Steps" in keys
    assert "ARCHITECTURE::Base Architecture" not in keys
    assert "IDENTITY::Base Architecture" in keys

    arch = test_client.get(
        "/api/rules?level=architecture&scope_key=SDXL 1.0", headers=headers
    )
    arch_items = arch.json()["items"]
    arch_keys = {item["rule_key"] for item in arch_items}
    assert "ARCHITECTURE::Base Architecture" in arch_keys

    resolved = test_client.get(
        "/api/rules/resolve?level=checkpoint&scope_key=alpha.safetensors"
        "&keys=GENERATION SETTINGS::Steps",
        headers=headers,
    )
    body = resolved.json()
    assert body["fields"]["GENERATION SETTINGS::Steps"]["status"] == "resolved"
    assert body["fields"]["GENERATION SETTINGS::Steps"]["value"] == "20"


def test_import_architecture_field_without_label_is_rejected(client, tmp_path, monkeypatch):
    monkeypatch.setenv("WORKBENCH_PROFILES_DIR", str(tmp_path))
    (tmp_path / "NoArch.txt").write_text(
        textwrap.dedent(
            """\
            [IDENTITY]
            Exact Checkpoint Filename: noarch.safetensors

            [ARCHITECTURE]
            Model Type: [作者说明] Checkpoint Merge

            [GENERATION SETTINGS]
            Steps: [作者推荐] 20
            """
        ),
        encoding="utf-8",
    )
    test_client, _ = client
    headers = {"Authorization": "Bearer test-session-token"}

    response = test_client.post(
        "/api/profiles/import", headers=headers, json={"file_name": "NoArch.txt"}
    )
    assert response.status_code == 200
    report = response.json()
    assert report["imported"] == 1
    rejected_keys = {item["rule_key"] for item in report["rejected"]}
    assert "ARCHITECTURE::Model Type" in rejected_keys


def test_import_missing_profile_returns_404(client, tmp_path, monkeypatch):
    test_client, _ = client
    _seed_profiles(tmp_path, monkeypatch)
    headers = {"Authorization": "Bearer test-session-token"}

    response = test_client.post(
        "/api/profiles/import", headers=headers, json={"file_name": "Nope.txt"}
    )
    assert response.status_code == 404


def test_import_profile_without_filename_is_rejected(client, tmp_path, monkeypatch):
    monkeypatch.setenv("WORKBENCH_PROFILES_DIR", str(tmp_path))
    (tmp_path / "NoId.txt").write_text(
        "[GENERATION SETTINGS]\nSteps: [作者推荐] 20\n", encoding="utf-8"
    )
    test_client, _ = client
    headers = {"Authorization": "Bearer test-session-token"}

    response = test_client.post(
        "/api/profiles/import", headers=headers, json={"file_name": "NoId.txt"}
    )
    assert response.status_code == 400


def test_import_profile_selective_candidate_keys(client, tmp_path, monkeypatch):
    test_client, _ = client
    _seed_profiles(tmp_path, monkeypatch)
    headers = {"Authorization": "Bearer test-session-token"}

    steps_key = "checkpoint\u001falpha.safetensors\u001fGENERATION SETTINGS::Steps"
    missing_key = "checkpoint\u001falpha.safetensors\u001fNO SUCH KEY"
    response = test_client.post(
        "/api/profiles/import",
        headers=headers,
        json={"file_name": "Alpha.txt", "candidate_keys": [steps_key, missing_key]},
    )
    assert response.status_code == 200
    report = response.json()
    assert report["selected"] is True
    assert report["imported"] == 1
    assert report["rejected"] == []
    assert report["unknown_keys"] == [missing_key]

    stored = test_client.get("/api/rules", headers=headers)
    keys = {item["rule_key"] for item in stored.json()["items"]}
    assert keys == {"GENERATION SETTINGS::Steps"}


def test_list_missing_directory_is_empty_not_error(client, monkeypatch):
    test_client, _ = client
    monkeypatch.setenv("WORKBENCH_PROFILES_DIR", "Z:/does/not/exist")
    headers = {"Authorization": "Bearer test-session-token"}

    response = test_client.get("/api/profiles", headers=headers)
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_profiles_dir_info_follows_env(client, tmp_path, monkeypatch):
    test_client, _ = client
    monkeypatch.setenv("WORKBENCH_PROFILES_DIR", str(tmp_path))
    headers = {"Authorization": "Bearer test-session-token"}

    response = test_client.get("/api/profiles/dir", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["path"] == str(tmp_path)
    assert body["exists"] is True


def test_open_profiles_dir_success(client, tmp_path, monkeypatch):
    test_client, _ = client
    monkeypatch.setenv("WORKBENCH_PROFILES_DIR", str(tmp_path))
    captured: dict[str, bool] = {}

    def fake_open():
        captured["called"] = True
        return {"path": str(tmp_path)}

    monkeypatch.setattr(profile_source, "open_profiles_dir", fake_open)
    headers = {"Authorization": "Bearer test-session-token"}

    response = test_client.post("/api/profiles/open-dir", headers=headers)
    assert response.status_code == 200
    assert response.json()["path"] == str(tmp_path)
    assert captured["called"] is True


def test_open_profiles_dir_missing_returns_404(client, monkeypatch):
    test_client, _ = client
    monkeypatch.setenv("WORKBENCH_PROFILES_DIR", "Z:/does/not/exist")
    headers = {"Authorization": "Bearer test-session-token"}

    response = test_client.post("/api/profiles/open-dir", headers=headers)
    assert response.status_code == 404


def test_open_profiles_dir_os_error_returns_500(client, monkeypatch):
    test_client, _ = client

    def fake_open():
        raise OSError("boom")

    monkeypatch.setattr(profile_source, "open_profiles_dir", fake_open)
    headers = {"Authorization": "Bearer test-session-token"}

    response = test_client.post("/api/profiles/open-dir", headers=headers)
    assert response.status_code == 500
