"""Structured normalization of legacy generation-parameter values.

Conservative by design: only well-formed numeric/structured facts are split out;
anything ambiguous keeps the original raw text under ``raw`` and the structured
field is ``None``. Ranges such as ``6~12``, ``30+`` and lists such as
``896×1152 / 832×1216`` are represented explicitly instead of being guessed
into a single number.

This module is pure: no filesystem, network, or store access.
"""

from __future__ import annotations

import re
from typing import Any

_NUM = r"\d+(?:\.\d+)?"
_RANGE = re.compile(rf"^(?P<lo>{_NUM})\s*(?:~|[-–—])\s*(?P<hi>{_NUM})$")
_RANGE_PLUS = re.compile(rf"^(?P<lo>{_NUM})\s*\+$")
_PLAIN_NUM = re.compile(rf"^(?P<lo>{_NUM})$")
_RESOLUTION = re.compile(rf"{_NUM}\s*[×x]\s*{_NUM}")
# Trailing parenthetical note: an applicability condition or example remark
# appended after the core value, e.g. ``Karras（Euler A 时）`` or
# ``25（使用指南参考，非强制固定值）``. Only a trailing bracket is removed;
# brackets inside a value or a second semicolon-separated set are untouched.
_TRAILING_PAREN = re.compile(r"\s*[（(][^（）()]*[）)]\s*$")


def _strip_trailing_parenthetical(text: str) -> str:
    cleaned = text.strip()
    previous = None
    while previous != cleaned:
        previous = cleaned
        cleaned = _TRAILING_PAREN.sub("", cleaned).strip(" ；;，,")
    return cleaned


def _to_number(text: str) -> int | float:
    return int(text) if "." not in text else float(text)


def normalize_number_range(raw: str) -> dict[str, Any] | None:
    """Parse a plain number, a range ``a~b``/``a-b`` or a ``n+`` floor."""
    text = raw.strip()
    match = _RANGE.match(text)
    if match:
        return {"kind": "range", "low": _to_number(match["lo"]), "high": _to_number(match["hi"])}
    match = _RANGE_PLUS.match(text)
    if match:
        return {"kind": "floor", "low": _to_number(match["lo"])}
    match = _PLAIN_NUM.match(text)
    if match:
        return {"kind": "value", "value": _to_number(match["lo"])}
    return None


def normalize_resolution(raw: str) -> dict[str, Any] | None:
    """Parse ``W×H`` resolutions anywhere in the text, including inside remarks.

    Unlike numeric/list fields, a resolution's own dimensions often sit inside
    a parenthetical note, so extraction runs against the original text instead
    of the trailing-remark-stripped copy. Duplicate sizes are de-duplicated
    while preserving first-seen order.
    """
    found = _RESOLUTION.findall(raw)
    if not found:
        return None
    resolutions: list[dict[str, int]] = []
    seen: set[tuple[int, int]] = set()
    for item in found:
        width, height = re.split(r"\s*[×x]\s*", item)
        pair = (int(width), int(height))
        if pair in seen:
            continue
        seen.add(pair)
        resolutions.append({"width": pair[0], "height": pair[1]})
    return {"kind": "resolutions", "items": resolutions}


def normalize_list(raw: str) -> dict[str, Any] | None:
    """Split a slash/comma list; a single clean token is a one-item list."""
    tokens = [token.strip() for token in re.split(r"\s*/\s*|，|,", raw) if token.strip()]
    if not tokens:
        return None
    return {"kind": "list", "items": tokens}


# Field key suffix (after ``SECTION::``) -> normalizer.
_FIELD_NORMALIZERS = {
    "Steps": normalize_number_range,
    "CFG": normalize_number_range,
    "Clip Skip": normalize_number_range,
    "Resolution": normalize_resolution,
    "Sampler": normalize_list,
    "Scheduler": normalize_list,
}


def normalize(rule_key: str, raw: str) -> dict[str, Any]:
    """Return ``{raw, structured}`` for one candidate rule key.

    ``structured`` is ``None`` when the value cannot be normalized confidently.
    """
    field_name = rule_key.split("::", 1)[1] if "::" in rule_key else rule_key
    normalizer = _FIELD_NORMALIZERS.get(field_name)
    # Numeric/list fields parse against a copy with trailing parenthetical
    # remarks removed; Resolution keeps the original text because its dimensions
    # may live inside a remark. The original raw text is kept untouched for
    # audit. A second semicolon-set value is not split here and stays
    # unstructured when ambiguous.
    cleaned = _strip_trailing_parenthetical(raw)
    source = raw if field_name == "Resolution" else cleaned
    structured = normalizer(source) if normalizer else None
    return {"raw": raw, "structured": structured}
