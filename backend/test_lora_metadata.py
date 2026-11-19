import json

import lora_metadata


def test_describe_complete_partial_missing_and_unreadable(tmp_path):
    (tmp_path / "good.safetensors").write_bytes(b"x")
    (tmp_path / "good.json").write_text(
        json.dumps(
            {
                "triggerWords": ["red hair", "school uniform"],
                "description": "A character LoRA for anime portraits.",
                "baseModel": "SD 1.5",
            }
        ),
        encoding="utf-8",
    )

    (tmp_path / "thin.safetensors").write_bytes(b"x")
    (tmp_path / "thin.json").write_text(
        json.dumps({"description": "Only a description."}), encoding="utf-8"
    )

    (tmp_path / "broken.safetensors").write_bytes(b"x")
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")

    (tmp_path / "plain.safetensors").write_bytes(b"x")

    good = lora_metadata.describe_lora(str(tmp_path), "good.safetensors")
    assert good["status"] == "complete"
    assert good["has_json"] is True
    assert good["trigger_words"] == ["red hair", "school uniform"]
    assert good["description"].startswith("A character LoRA")
    assert good["base_model"] == "SD 1.5"

    thin = lora_metadata.describe_lora(str(tmp_path), "thin.safetensors")
    assert thin["status"] == "partial"
    assert thin["description"] == "Only a description."

    broken = lora_metadata.describe_lora(str(tmp_path), "broken.safetensors")
    assert broken["status"] == "unreadable"
    assert broken["has_json"] is True

    plain = lora_metadata.describe_lora(str(tmp_path), "plain.safetensors")
    assert plain["status"] == "missing"
    assert plain["has_json"] is False


def test_describe_rejects_traversal_and_unconfigured_dir(tmp_path):
    traversal = lora_metadata.describe_lora(str(tmp_path), "../evil.safetensors")
    assert traversal["status"] == "missing"

    unconfigured = lora_metadata.describe_lora("", "good.safetensors")
    assert unconfigured["status"] == "missing"

    # Subfolder-relative names resolve inside the configured directory.
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "nested.safetensors").write_bytes(b"x")
    (sub / "nested.json").write_text(
        json.dumps({"tags": ["one", "two"]}), encoding="utf-8"
    )
    nested = lora_metadata.describe_lora(str(tmp_path), "sub/nested.safetensors")
    assert nested["status"] == "partial"
    assert nested["trigger_words"] == ["one", "two"]


def test_describe_empty_dict_and_non_dict_json(tmp_path):
    (tmp_path / "nodata.safetensors").write_bytes(b"x")
    (tmp_path / "nodata.json").write_text("{}", encoding="utf-8")
    nodata = lora_metadata.describe_lora(str(tmp_path), "nodata.safetensors")
    assert nodata["status"] == "empty"
    assert nodata["trigger_words"] == []
    assert nodata["description"] == ""
    assert nodata["base_model"] == ""

    (tmp_path / "array.safetensors").write_bytes(b"x")
    (tmp_path / "array.json").write_text("[1, 2, 3]", encoding="utf-8")
    array = lora_metadata.describe_lora(str(tmp_path), "array.safetensors")
    assert array["status"] == "empty"

    (tmp_path / "scalar.safetensors").write_bytes(b"x")
    (tmp_path / "scalar.json").write_text('"just a string"', encoding="utf-8")
    scalar = lora_metadata.describe_lora(str(tmp_path), "scalar.safetensors")
    assert scalar["status"] == "empty"


def test_scan_groups_by_name(tmp_path):
    (tmp_path / "a.safetensors").write_bytes(b"x")
    (tmp_path / "a.json").write_text(
        json.dumps({"triggerWords": ["a word"], "baseModel": "SDXL"}),
        encoding="utf-8",
    )
    (tmp_path / "b.safetensors").write_bytes(b"x")

    report = lora_metadata.scan_lora_metadata(
        str(tmp_path), ["a.safetensors", "b.safetensors"]
    )
    assert report["a.safetensors"]["status"] == "complete"
    assert report["b.safetensors"]["status"] == "missing"


def test_manual_note_overrides_sidecar_and_keeps_combos(tmp_path):
    sidecar_dir = tmp_path / "sidecar"
    sidecar_dir.mkdir()
    (sidecar_dir / "hero.safetensors").write_bytes(b"x")
    (sidecar_dir / "hero.json").write_text(
        json.dumps(
            {
                "trigger_words": ["old trigger"],
                "description": "sidecar description",
                "base_model": "SD 1.5",
            }
        ),
        encoding="utf-8",
    )

    manual_dir = tmp_path / "manual" / "lora"
    manual_dir.mkdir(parents=True)
    (manual_dir / "hero.json").write_text(
        json.dumps(
            {
                "trigger_words": ["hero name", "old trigger"],
                "description": "curated note",
                "combos": [
                    {"name": "outfit A", "trigger_words": ["dress"]},
                    {"trigger_words": ["solo"]},
                ],
            }
        ),
        encoding="utf-8",
    )

    report = lora_metadata.scan_lora_metadata(
        str(sidecar_dir), ["hero.safetensors"], manual_dir=str(manual_dir)
    )
    meta = report["hero.safetensors"]
    assert meta["source"] == "manual"
    assert meta["manual_present"] is True
    assert meta["trigger_words"] == ["hero name", "old trigger"]
    assert meta["description"] == "curated note"
    # Manual note omits base_model, so the sidecar value survives.
    assert meta["base_model"] == "SD 1.5"
    assert meta["combos"] == [
        {"name": "outfit A", "trigger_words": ["dress"]},
        {"name": "", "trigger_words": ["solo"]},
    ]


def test_manual_missing_falls_back_to_sidecar(tmp_path):
    sidecar_dir = tmp_path / "sidecar"
    sidecar_dir.mkdir()
    (sidecar_dir / "plain.safetensors").write_bytes(b"x")
    (sidecar_dir / "plain.json").write_text(
        json.dumps({"trigger_words": ["sidecar trigger"]}), encoding="utf-8"
    )
    manual_dir = tmp_path / "manual"
    manual_dir.mkdir()

    report = lora_metadata.scan_lora_metadata(
        str(sidecar_dir), ["plain.safetensors"], manual_dir=str(manual_dir)
    )
    meta = report["plain.safetensors"]
    assert meta["source"] == "sidecar"
    assert meta["trigger_words"] == ["sidecar trigger"]
    assert meta["combos"] == []


def test_manual_unreadable_falls_back_to_sidecar(tmp_path):
    sidecar_dir = tmp_path / "sidecar"
    sidecar_dir.mkdir()
    (sidecar_dir / "broken.safetensors").write_bytes(b"x")
    (sidecar_dir / "broken.json").write_text(
        json.dumps({"description": "sidecar still readable"}), encoding="utf-8"
    )
    manual_dir = tmp_path / "manual"
    manual_dir.mkdir()
    (manual_dir / "broken.json").write_text("{not json", encoding="utf-8")

    report = lora_metadata.scan_lora_metadata(
        str(sidecar_dir), ["broken.safetensors"], manual_dir=str(manual_dir)
    )
    meta = report["broken.safetensors"]
    assert meta["manual_present"] is True
    assert meta["manual_unreadable"] is True
    assert meta["description"] == "sidecar still readable"


def test_manual_path_rejects_traversal(tmp_path):
    manual_dir = tmp_path / "manual"
    manual_dir.mkdir()
    result = lora_metadata.load_manual(str(manual_dir), "../evil.safetensors")
    assert result["present"] is False
