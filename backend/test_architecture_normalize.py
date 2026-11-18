import architecture_normalize as an


def test_sdxl_variants_normalize_to_same_family():
    for label in ("SDXL", "SDXL 1.0", "sdxl", " SDXL 1.0 "):
        result = an.normalize(label)
        assert result["matched"] is True
        assert result["canonical"] == "SDXL"
        assert result["mixed"] is False
    assert an.same_family("SDXL", "SDXL 1.0") is True


def test_sd15_is_distinct_from_sdxl():
    result = an.normalize("SD1.5")
    assert result["canonical"] == "SD1.5"
    assert an.same_family("SD1.5", "SDXL 1.0") is False


def test_pony_is_its_own_family():
    result = an.normalize("Pony")
    assert result["canonical"] == "Pony"
    assert an.same_family("Pony", "SDXL") is False


def test_mixed_pony_sdxl_label_is_flagged_mixed():
    result = an.normalize("Pony / SDXL 系")
    assert result["matched"] is True
    assert result["mixed"] is True
    assert result["canonical"] == "Pony"


def test_derived_illustrious_label_is_mixed_not_plain_sdxl():
    result = an.normalize("Illustrious SDXL 系")
    assert result["matched"] is True
    assert result["mixed"] is True
    assert result["canonical"] == "SDXL"


def test_unrecognized_label_stays_other():
    result = an.normalize("微调自 IL-XL")
    assert result["matched"] is False
    assert result["canonical"] is None
    assert result["family"] == "other"


def test_empty_label_is_unmatched():
    for label in (None, "", "   "):
        result = an.normalize(label)
        assert result["matched"] is False
        assert result["canonical"] is None


def test_same_family_requires_both_matched():
    assert an.same_family("SDXL", "未知底座") is False
    assert an.same_family(None, "SDXL") is False
