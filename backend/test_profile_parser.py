import textwrap

import profile_parser


SAMPLE = textwrap.dedent(
    """\
    # MODEL PROFILE — IntoRealism Ultra V8

    [IDENTITY]
    Display Name: IntoRealism Ultra V8
    Exact Checkpoint Filename: intorealismUltra_v80.safetensors
    Version: V8.0（SHA256 一致，已核实版本身份）

    [ARCHITECTURE]
    Base Architecture: [已核实] SDXL 1.0
    Model Type: [作者说明] DMD2 + Light 混合；早期测试版本
    VAE: 未给出
    Clip Skip: 未给出

    [GENERATION SETTINGS]
    Resolution: [作者推荐] 896×1152 / 832×1216
    Steps: [作者推荐] 6~12
    CFG: 未给出

    [PROMPT STYLE]
    Author Positive Example: 完整官方正面范例未找到
    """
)


def test_extract_filename_display_and_architecture():
    parsed = profile_parser.parse_profile_text(SAMPLE, "IntoRealism_Ultra_V8.txt")
    assert parsed.filename == "intorealismUltra_v80.safetensors"
    assert parsed.display_name == "IntoRealism Ultra V8"
    assert parsed.architecture == "SDXL 1.0"


def test_missing_fields_are_unknown_without_candidates():
    parsed = profile_parser.parse_profile_text(SAMPLE)
    unknown_keys = [item.split("::")[1] for item in parsed.unknown_fields]
    assert "VAE" in unknown_keys
    assert "Clip Skip" in unknown_keys
    assert "CFG" in unknown_keys
    # No candidate emitted for a missing field.
    keys = {c.key for c in parsed.candidates}
    assert "VAE" not in keys
    assert "Clip Skip" not in keys
    assert "CFG" not in keys


def test_provenance_and_confidence_mapping():
    parsed = profile_parser.parse_profile_text(SAMPLE)
    by_key = {c.key: c for c in parsed.candidates}

    arch = by_key["Base Architecture"]
    assert arch.provenance == "verified_mirror"
    assert arch.confidence == "partial"

    model_type = by_key["Model Type"]
    assert model_type.provenance == "author"
    assert model_type.confidence == "partial"

    resolution = by_key["Resolution"]
    assert resolution.provenance == "author"
    assert resolution.confidence == "authoritative"


def test_candidates_to_records_shape():
    parsed = profile_parser.parse_profile_text(SAMPLE)
    records = profile_parser.candidates_to_records(
        parsed, level="checkpoint", scope_key="intorealismUltra_v80.safetensors"
    )
    assert records, "expected at least one candidate"
    arch_records = [r for r in records if r["rule_key"].startswith("ARCHITECTURE::")]
    other_records = [r for r in records if not r["rule_key"].startswith("ARCHITECTURE::")]
    assert arch_records, "expected architecture-section records"
    assert all(r["level"] == "architecture" for r in arch_records)
    assert all(r["scope_key"] == "SDXL 1.0" for r in arch_records)
    assert all(r["level"] == "checkpoint" for r in other_records)
    assert all(r["scope_key"] == "intorealismUltra_v80.safetensors" for r in other_records)
    assert "source_raw" in records[0]
    # Missing fields must not project into records.
    assert all("CFG" != r["rule_key"].split("::")[1] for r in records)


def test_community_note_maps_to_unverified():
    text = "[GENERATION SETTINGS]\nSteps: 社区参考 20~30 步（待核实）\n"
    parsed = profile_parser.parse_profile_text(text)
    candidate = parsed.candidates[0]
    assert candidate.provenance == "community"
    assert candidate.confidence == "unverified"
