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
