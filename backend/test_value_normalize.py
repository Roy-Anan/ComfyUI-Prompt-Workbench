import profile_parser
import value_normalize


def test_number_range_and_value():
    assert value_normalize.normalize_number_range("6~12") == {"kind": "range", "low": 6, "high": 12}
    assert value_normalize.normalize_number_range("30~32") == {"kind": "range", "low": 30, "high": 32}
    assert value_normalize.normalize_number_range("7") == {"kind": "value", "value": 7}
    assert value_normalize.normalize_number_range("1.5~2") == {"kind": "range", "low": 1.5, "high": 2}
    assert value_normalize.normalize_number_range("30+") == {"kind": "floor", "low": 30}


def test_number_unparseable_stays_none():
    assert value_normalize.normalize_number_range("低步低 CFG") is None
    assert value_normalize.normalize_number_range("待核实") is None


def test_resolution_list():
    parsed = value_normalize.normalize_resolution("896×1152 / 832×1216")
    assert parsed == {
        "kind": "resolutions",
        "items": [
            {"width": 896, "height": 1152},
            {"width": 832, "height": 1216},
        ],
    }
    assert value_normalize.normalize_resolution("SDXL 友好分辨率") is None


def test_resolution_keeps_sizes_inside_parenthetical():
    parsed = value_normalize.normalize(
        "GENERATION SETTINGS::Resolution",
        "系列普通版友好分辨率（768×1152 / 648×1152 / 864×1152，待核对 V3）",
    )
    assert parsed["structured"] == {
        "kind": "resolutions",
        "items": [
            {"width": 768, "height": 1152},
            {"width": 648, "height": 1152},
            {"width": 864, "height": 1152},
        ],
    }


def test_resolution_de_duplicates_repeated_sizes():
    parsed = value_normalize.normalize_resolution("832×1216 / 832×1216")
    assert parsed["items"] == [{"width": 832, "height": 1216}]


def test_sampler_list():
    parsed = value_normalize.normalize_list("DPM++ SDE Karras / Euler a")
    assert parsed == {
        "kind": "list",
        "items": ["DPM++ SDE Karras", "Euler a"],
    }


def test_normalize_routes_by_field_key():
    steps = value_normalize.normalize("GENERATION SETTINGS::Steps", "6~12")
    assert steps["structured"] == {"kind": "range", "low": 6, "high": 12}
    cfg_text = value_normalize.normalize("GENERATION SETTINGS::CFG", "低步低 CFG")
    assert cfg_text["structured"] is None
    assert cfg_text["raw"] == "低步低 CFG"


def test_trailing_parenthetical_remark_is_stripped_before_parse():
    steps = value_normalize.normalize("GENERATION SETTINGS::Steps", "25（使用指南参考，非强制固定值）")
    assert steps["structured"] == {"kind": "value", "value": 25}
    assert steps["raw"] == "25（使用指南参考，非强制固定值）"

    cfg = value_normalize.normalize("GENERATION SETTINGS::CFG", "12（示例图参数，不要覆盖作者推荐的 6~8）")
    assert cfg["structured"] == {"kind": "value", "value": 12}

    scheduler = value_normalize.normalize("GENERATION SETTINGS::Scheduler", "Karras（Euler A 时）")
    assert scheduler["structured"] == {"kind": "list", "items": ["Karras"]}
    assert scheduler["raw"] == "Karras（Euler A 时）"


def test_single_token_sampler_is_one_item_list():
    parsed = value_normalize.normalize_list("LCM")
    assert parsed == {"kind": "list", "items": ["LCM"]}


def test_two_semicolon_sets_stay_unstructured():
    steps = value_normalize.normalize("GENERATION SETTINGS::Steps", "35；25~40")
    assert steps["structured"] is None


def test_candidate_records_carry_structured():
    text = (
        "[IDENTITY]\n"
        "Exact Checkpoint Filename: demo.safetensors\n"
        "[GENERATION SETTINGS]\n"
        "Steps: [作者推荐] 6~12\n"
        "CFG: [作者推荐] 1.5~2\n"
        "Resolution: [作者推荐] 896×1152 / 832×1216\n"
        "Sampler: [作者推荐] Euler A / Exponential\n"
    )
    parsed = profile_parser.parse_profile_text(text, "demo.txt")
    records = profile_parser.candidates_to_records(parsed, "checkpoint", "demo.safetensors")
    by_key = {r["rule_key"]: r for r in records}

    assert by_key["GENERATION SETTINGS::Steps"]["structured"] == {
        "kind": "range", "low": 6, "high": 12
    }
    assert by_key["GENERATION SETTINGS::Resolution"]["structured"]["kind"] == "resolutions"
    assert by_key["GENERATION SETTINGS::Sampler"]["structured"]["kind"] == "list"
    for record in records:
        assert "structured" in record
