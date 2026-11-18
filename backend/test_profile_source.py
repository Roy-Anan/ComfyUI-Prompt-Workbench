import textwrap


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
    assert len(records) == 2
    steps = next(r for r in records if r["rule_key"] == "GENERATION SETTINGS::Steps")
    assert steps["level"] == "checkpoint"
    assert steps["scope_key"] == "alpha.safetensors"
    assert steps["value"] == "20"
    assert steps["provenance"] == "author"
    assert steps["confidence"] == "authoritative"
    # Preview must not have persisted anything.
    stored = test_client.get("/api/rules", headers=headers)
    assert stored.json()["items"] == []


def test_preview_profile_unknown_file_returns_404(client, tmp_path, monkeypatch):
    test_client, _ = client
    _seed_profiles(tmp_path, monkeypatch)
    headers = {"Authorization": "Bearer test-session-token"}

    response = test_client.get("/api/profiles/Missing.txt", headers=headers)
    assert response.status_code == 404


def test_list_missing_directory_is_empty_not_error(client, monkeypatch):
    test_client, _ = client
    monkeypatch.setenv("WORKBENCH_PROFILES_DIR", "Z:/does/not/exist")
    headers = {"Authorization": "Bearer test-session-token"}

    response = test_client.get("/api/profiles", headers=headers)
    assert response.status_code == 200
    assert response.json()["items"] == []
