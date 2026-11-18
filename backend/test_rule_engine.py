import pytest

import rule_engine
from rule_engine import RuleRecord, RuleError


def _record(**overrides):
    defaults = dict(
        level="global",
        scope_key=None,
        key="steps",
        value=20,
        provenance="community",
        confidence="unverified",
        version="1",
        note="",
    )
    defaults.update(overrides)
    return RuleRecord(**defaults)


def test_checkpoint_rule_overrides_architecture_and_global():
    rules = [
        _record(level="global", key="steps", value=20),
        _record(level="architecture", scope_key="sdxl", key="steps", value=28),
        _record(level="checkpoint", scope_key="pony.safetensors", key="steps", value=32),
    ]
    result = rule_engine.resolve_field(rules, "checkpoint", "pony.safetensors", "steps")
    assert result["status"] == "resolved"
    assert result["value"] == 32
    assert result["source_level"] == "checkpoint"


def test_architecture_falls_back_to_global():
    rules = [
        _record(level="global", key="cfg", value=7),
        _record(level="architecture", scope_key="sd15", key="cfg", value=6),
    ]
    result = rule_engine.resolve_field(rules, "architecture", "sd15", "cfg")
    assert result["status"] == "resolved"
    assert result["value"] == 6
    assert result["source_level"] == "architecture"

    fallback = rule_engine.resolve_field(rules, "architecture", "sdxl", "cfg")
    assert fallback["status"] == "resolved"
    assert fallback["value"] == 7
    assert fallback["source_level"] == "global"


def test_uncovered_field_is_unknown_not_defaulted():
    rules = [_record(level="global", key="steps", value=20)]
    result = rule_engine.resolve_field(rules, "checkpoint", "pony.safetensors", "clip_skip")
    assert result["status"] == "unknown"
    assert result["value"] is None
    assert result["source_level"] is None


def test_same_level_conflict_is_marked_not_picked():
    rules = [
        _record(level="checkpoint", scope_key="pony.safetensors", key="cfg", value=7),
        _record(
            level="checkpoint",
            scope_key="pony.safetensors",
            key="cfg",
            value=5,
            provenance="author",
        ),
    ]
    result = rule_engine.resolve_field(rules, "checkpoint", "pony.safetensors", "cfg")
    assert result["status"] == "conflict"
    assert result["value"] is None
    assert len(result["sources"]) == 2


def test_checkpoint_rule_does_not_leak_into_architecture_context():
    rules = [
        _record(level="checkpoint", scope_key="pony.safetensors", key="steps", value=32),
        _record(level="global", key="steps", value=20),
    ]
    result = rule_engine.resolve_field(rules, "architecture", "sdxl", "steps")
    assert result["status"] == "resolved"
    assert result["value"] == 20
    assert result["source_level"] == "global"


def test_resolve_context_reports_conflicts_and_unknowns():
    rules = [
        _record(level="global", key="steps", value=20),
        _record(level="checkpoint", scope_key="pony.safetensors", key="cfg", value=7),
        _record(level="checkpoint", scope_key="pony.safetensors", key="cfg", value=5),
    ]
    context = rule_engine.resolve_context(
        rules, "checkpoint", "pony.safetensors", ["steps", "cfg", "trigger"]
    )
    assert context["conflicts"] == ["cfg"]
    assert context["unknown"] == ["trigger"]
    assert context["fields"]["steps"]["source_level"] == "global"


def test_record_validates_level_and_provenance():
    with pytest.raises(RuleError):
        _record(level="avatar").validate()
    with pytest.raises(RuleError):
        _record(level="checkpoint", scope_key=None).validate()
    with pytest.raises(RuleError):
        _record(provenance="unknown-source").validate()


def test_summarize_rules_by_level():
    rules = [
        _record(level="global", key="steps", value=20),
        _record(level="checkpoint", scope_key="pony.safetensors", key="cfg", value=7),
    ]
    summary = rule_engine.summarize_rules(rules)
    assert summary["global"]["count"] == 1
    assert summary["checkpoint"]["count"] == 1
    assert "pony.safetensors" in summary["checkpoint"]["scopes"]
