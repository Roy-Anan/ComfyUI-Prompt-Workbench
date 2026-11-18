import rule_compare


def _field(key, status="resolved", value=None, structured=None, source_level="checkpoint"):
    return {
        "key": key,
        "status": status,
        "value": value,
        "structured": structured,
        "source_level": source_level,
        "source": {"provenance": "author", "confidence": "partial"},
    }


def test_steps_in_range_matches():
    rule = _field(
        "GENERATION SETTINGS::Steps",
        value="6~12",
        structured={"kind": "range", "low": 6, "high": 12},
    )
    verdict = rule_compare.compare_rule(rule, {"steps": 10, "cfg": 2.0})
    assert verdict["status"] == "match"
    assert verdict["actual"] == 10


def test_steps_out_of_range_reported():
    rule = _field(
        "GENERATION SETTINGS::Steps",
        value="6~12",
        structured={"kind": "range", "low": 6, "high": 12},
    )
    verdict = rule_compare.compare_rule(rule, {"steps": 30})
    assert verdict["status"] == "out_of_range"


def test_cfg_floor_match_and_mismatch():
    floor = {"kind": "floor", "low": 1.5}
    assert rule_compare.compare_rule(_field("GENERATION SETTINGS::CFG", structured=floor), {"cfg": 2.0})["status"] == "match"
    assert rule_compare.compare_rule(_field("GENERATION SETTINGS::CFG", structured=floor), {"cfg": 1.0})["status"] == "out_of_range"


def test_sampler_list_match():
    rule = _field(
        "GENERATION SETTINGS::Sampler",
        structured={"kind": "list", "items": ["euler a karras", "euler"]},
    )
    verdict = rule_compare.compare_rule(rule, {"sampler_name": "Euler A Karras"})
    assert verdict["status"] == "match"


def test_scheduler_list_match_after_note_strip():
    rule = _field(
        "GENERATION SETTINGS::Scheduler",
        value="Karras（Euler A 时）",
        structured={"kind": "list", "items": ["Karras"]},
    )
    verdict = rule_compare.compare_rule(rule, {"scheduler": "karras"})
    assert verdict["status"] == "match"


def test_non_numeric_actual_stays_unknown():
    rule = _field(
        "GENERATION SETTINGS::Steps",
        structured={"kind": "range", "low": 6, "high": 12},
    )
    verdict = rule_compare.compare_rule(rule, {"steps": "auto"})
    assert verdict["status"] == "unknown"
    assert verdict["reason"] == "actual_not_numeric"


def test_unstructured_rule_stays_unknown():
    rule = _field("GENERATION SETTINGS::Steps", value="6~12（示例）", structured=None)
    verdict = rule_compare.compare_rule(rule, {"steps": 10})
    assert verdict["status"] == "unknown"
    assert verdict["reason"] == "rule_not_structured"


def test_conflict_rule_passthrough_unknown():
    rule = _field("GENERATION SETTINGS::CFG", status="conflict", value=None)
    verdict = rule_compare.compare_rule(rule, {"cfg": 7})
    assert verdict["status"] == "unknown"
    assert verdict["reason"] == "rule_conflict"


def test_compare_workflow_counts():
    payload = {
        "status": "registered",
        "checkpoint": "pony.safetensors",
        "architecture": "SD1.5",
        "fields": [
            _field("GENERATION SETTINGS::Steps", structured={"kind": "range", "low": 6, "high": 12}),
            _field("MODEL BEHAVIOR::Strengths", structured=None),
        ],
    }
    result = rule_compare.compare_workflow(payload, {"steps": 10})
    assert result["status"] == "registered"
    assert result["counts"].get("match") == 1
    assert result["counts"].get("unknown") == 1
