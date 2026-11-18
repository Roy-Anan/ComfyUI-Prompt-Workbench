import rule_prompt


def _row(level, scope_key, key, value, provenance="author", confidence="partial"):
    return {
        "level": level,
        "scope_key": scope_key,
        "rule_key": key,
        "value": value,
        "structured": None,
        "provenance": provenance,
        "confidence": confidence,
        "version": "legacy-1",
        "note": "",
    }


def test_build_prompt_resolves_inheritance_and_keeps_source():
    context = {
        "status": "registered",
        "checkpoint": "pony.safetensors",
        "architecture": "SD1.5",
        "checkpoint_rules": [_row("checkpoint", "pony.safetensors", "GENERATION SETTINGS::Steps", 32)],
        "architecture_rules": [
            _row("architecture", "SD1.5", "GENERATION SETTINGS::Steps", 28),
            _row("architecture", "SD1.5", "ARCHITECTURE::Model Type", "Checkpoint"),
        ],
        "global_rules": [_row("global", None, "GENERATION SETTINGS::Scheduler", "Karras")],
    }
    payload = rule_prompt.build_prompt_context(context)

    assert payload["status"] == "registered"
    assert payload["checkpoint"] == "pony.safetensors"
    assert payload["architecture"] == "SD1.5"
    fields = {f["key"]: f for f in payload["fields"]}

    steps = fields["GENERATION SETTINGS::Steps"]
    assert steps["status"] == "resolved"
    assert steps["value"] == 32
    assert steps["source_level"] == "checkpoint"
    assert steps["source"]["provenance"] == "author"

    arch_type = fields["ARCHITECTURE::Model Type"]
    assert arch_type["source_level"] == "architecture"

    scheduler = fields["GENERATION SETTINGS::Scheduler"]
    assert scheduler["source_level"] == "global"

    assert payload["conflicts"] == []
    assert payload["unknown"] == []
    assert "checkpoint 规则优先" in payload["instruction"]


def test_build_prompt_marks_same_level_conflict():
    context = {
        "status": "registered",
        "checkpoint": "pony.safetensors",
        "architecture": None,
        "checkpoint_rules": [
            _row("checkpoint", "pony.safetensors", "GENERATION SETTINGS::CFG", 7),
            _row("checkpoint", "pony.safetensors", "GENERATION SETTINGS::CFG", 6),
        ],
        "architecture_rules": [],
        "global_rules": [],
    }
    payload = rule_prompt.build_prompt_context(context)
    cfg = next(f for f in payload["fields"] if f["key"] == "GENERATION SETTINGS::CFG")
    assert cfg["status"] == "conflict"
    assert cfg["value"] is None
    assert len(cfg["sources"]) == 2
    assert payload["conflicts"] == ["GENERATION SETTINGS::CFG"]


def test_build_prompt_unregistered_carries_no_rules():
    payload = rule_prompt.build_prompt_context(
        {
            "status": "unregistered",
            "checkpoint": "ghost.safetensors",
            "architecture": None,
            "checkpoint_rules": [],
            "architecture_rules": [],
            "global_rules": [],
        }
    )
    assert payload["status"] == "unregistered"
    assert payload["fields"] == []
    assert "未在规则库登记" in payload["instruction"]
