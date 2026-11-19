import json
import sqlite3

import pytest

import rule_store
import rule_engine
from rule_engine import RuleError


@pytest.fixture()
def connection(tmp_path):
    conn = sqlite3.connect(tmp_path / "rules.sqlite3", timeout=10)
    conn.row_factory = sqlite3.Row
    rule_store.ensure_schema(conn)
    yield conn
    conn.close()


def test_upsert_and_lookup_round_trip(connection):
    record = rule_store.upsert_rule(
        connection,
        level="checkpoint",
        scope_key="pony.safetensors",
        rule_key="steps",
        value=32,
        provenance="author",
        confidence="authoritative",
        version="2",
        note="官方范例",
    )
    assert record["value"] == 32
    assert record["provenance"] == "author"

    found = rule_store.lookup_rule(connection, "checkpoint", "pony.safetensors", "steps")
    assert found["value"] == 32
    assert found["note"] == "官方范例"


def test_upsert_replaces_same_triple(connection):
    rule_store.upsert_rule(connection, "global", None, "cfg", 7, version="1")
    rule_store.upsert_rule(connection, "global", None, "cfg", 6, version="2")
    rows = rule_store.list_rules(connection, level="global")
    assert len(rows) == 1
    assert rows[0]["value"] == 6
    assert rows[0]["version"] == "2"


def test_json_value_round_trip(connection):
    rule_store.upsert_rule(connection, "architecture", "sdxl", "tags", ["1girl", "long hair"])
    found = rule_store.lookup_rule(connection, "architecture", "sdxl", "tags")
    assert found["value"] == ["1girl", "long hair"]


def test_list_filters_by_level_and_scope(connection):
    rule_store.upsert_rule(connection, "global", None, "steps", 20)
    rule_store.upsert_rule(connection, "checkpoint", "pony.safetensors", "steps", 32)
    global_rows = rule_store.list_rules(connection, level="global")
    assert [row["rule_key"] for row in global_rows] == ["steps"]

    ckpt = rule_store.list_rules(connection, level="checkpoint", scope_key="pony.safetensors")
    assert len(ckpt) == 1


def test_delete_rule(connection):
    rule_store.upsert_rule(connection, "global", None, "cfg", 7)
    assert rule_store.delete_rule(connection, "global", "", "cfg") is True
    assert rule_store.delete_rule(connection, "global", "", "cfg") is False
    assert rule_store.list_rules(connection) == []


def test_invalid_record_rejected_before_store(connection):
    with pytest.raises(RuleError):
        rule_store.upsert_rule(connection, "avatar", None, "steps", 20)
    assert rule_store.list_rules(connection) == []


def test_load_records_feed_engine_resolution(connection):
    rule_store.upsert_rule(connection, "global", None, "steps", 20)
    rule_store.upsert_rule(connection, "architecture", "sdxl", "steps", 28)
    rule_store.upsert_rule(connection, "checkpoint", "pony.safetensors", "steps", 32)

    context = rule_store.resolve_stored(
        connection, "checkpoint", "pony.safetensors", ["steps", "clip_skip"]
    )
    assert context["fields"]["steps"]["value"] == 32
    assert context["fields"]["steps"]["source_level"] == "checkpoint"
    assert context["unknown"] == ["clip_skip"]


def test_context_groups_same_family_architecture_variants(connection):
    rule_store.upsert_rule(
        connection, "checkpoint", "xl-model.safetensors",
        "GENERATION SETTINGS::Steps", "28",
    )
    # Base Architecture fact landed in the architecture bucket on import.
    rule_store.upsert_rule(
        connection, "architecture", "SDXL 1.0",
        "ARCHITECTURE::Base Architecture", "SDXL 1.0",
    )
    # Same family under a variant label; must be inherited too.
    rule_store.upsert_rule(
        connection, "architecture", "SDXL",
        "ARCHITECTURE::Model Type", "Checkpoint",
    )
    # Different family must not leak into this context.
    rule_store.upsert_rule(
        connection, "architecture", "SD1.5",
        "ARCHITECTURE::Model Type", "Checkpoint",
    )

    context = rule_store.context_for_checkpoint(connection, "xl-model.safetensors")
    assert context["status"] == "registered"
    assert context["architecture_family"] == "SDXL"
    arch_scopes = {row["scope_key"] for row in context["architecture_rules"]}
    assert arch_scopes == {"SDXL 1.0", "SDXL"}


def test_upsert_archives_previous_version(connection):
    rule_store.upsert_rule(connection, "global", None, "cfg", 7, version="1", note="首版")
    rule_store.upsert_rule(connection, "global", None, "cfg", 6, version="2", note="修订")

    history = rule_store.list_history(connection, level="global", rule_key="cfg")
    assert len(history) == 1
    assert history[0]["value"] == 7
    assert history[0]["version"] == "1"
    assert history[0]["note"] == "首版"
    assert history[0]["reason"] == "upsert"


def test_restore_history_rolls_back_and_archives_current(connection):
    rule_store.upsert_rule(connection, "global", None, "cfg", 7, version="1")
    rule_store.upsert_rule(connection, "global", None, "cfg", 6, version="2")
    history = rule_store.list_history(connection, level="global", rule_key="cfg")
    old_id = history[0]["history_id"]

    restored = rule_store.restore_history(connection, old_id)
    assert restored["value"] == 7
    assert restored["version"] == "1"

    current = rule_store.lookup_rule(connection, "global", "", "cfg")
    assert current["value"] == 7

    trail = rule_store.list_history(connection, level="global", rule_key="cfg")
    # The pre-restore value (6) is archived under reason restore.
    assert any(item["value"] == 6 and item["reason"] == "restore" for item in trail)


def test_restore_missing_history_returns_none(connection):
    rule_store.upsert_rule(connection, "global", None, "cfg", 7)
    assert rule_store.restore_history(connection, 99999) is None


def test_context_keeps_mixed_label_separate_from_plain_family(connection):
    rule_store.upsert_rule(
        connection, "checkpoint", "pony-xl.safetensors",
        "GENERATION SETTINGS::Steps", "24",
    )
    rule_store.upsert_rule(
        connection, "architecture", "Pony / SDXL 系",
        "ARCHITECTURE::Base Architecture", "Pony / SDXL 系",
    )
    rule_store.upsert_rule(
        connection, "architecture", "SDXL",
        "ARCHITECTURE::Model Type", "Checkpoint",
    )

    context = rule_store.context_for_checkpoint(connection, "pony-xl.safetensors")
    arch_scopes = {row["scope_key"] for row in context["architecture_rules"]}
    # The mixed label must not inherit the plain SDXL family rules.
    assert arch_scopes == {"Pony / SDXL 系"}
