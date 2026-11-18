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
    """Parse slash-separated ``W×H`` resolutions; keep non-resolution text aside."""
    found = _RESOLUTION.findall(raw)
    if not found:
        return None
    resolutions: list[dict[str, int]] = []
    for item in found:
        width, height = re.split(r"\s*[×x]\s*", item)
        resolutions.append({"width": int(width), "height": int(height)})
    return {"kind": "resolutions", "items": resolutions}


def normalize_list(raw: str) -> dict[str, Any] | None:
    """Split a slash/comma list when at least two clean tokens exist."""
    tokens = [token.strip() for token in re.split(r"\s*/\s*|，|,", raw) if token.strip()]
    if len(tokens) < 2:
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
    structured = normalizer(raw) if normalizer else None
    return {"raw": raw, "structured": structured}
