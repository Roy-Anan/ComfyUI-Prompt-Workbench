"""Conservative comparison between stored rule values and workflow parameters.

This slice only judges facts it can read from both sides:

  * rule facts keep their structured shape produced by :mod:`value_normalize`
    (range / floor / value / resolutions / list);
  * workflow actuals come from the sampler node params snapshot;
  * a comparison that cannot be decided confidently is reported ``unknown``
    instead of guessing a match or a conflict.

No writing, no LLM call, no ComfyUI/Ollama contact here.
"""

from __future__ import annotations

from typing import Any

# Rule field suffix -> sampler actual param key.
_FIELD_TO_ACTUAL = {
    "Steps": "steps",
    "CFG": "cfg",
    "Clip Skip": "clip_skip",
    "Sampler": "sampler_name",
    "Scheduler": "scheduler",
}
# Resolution is compared against the latent node's width/height pair.
_RESOLUTION_FIELD = "Resolution"


def _field_name(rule_key: str) -> str:
    return rule_key.split("::", 1)[1] if "::" in rule_key else rule_key


def _actual_number(actual: Any) -> float | int | None:
    if isinstance(actual, bool):
        return None
    if isinstance(actual, (int, float)):
        return actual
    if isinstance(actual, str):
        text = actual.strip()
        try:
            return float(text) if "." in text else int(text)
        except ValueError:
            return None
    return None


def _compare_number(structured: dict[str, Any], actual: Any) -> dict[str, Any]:
    number = _actual_number(actual)
    if number is None:
        return {"status": "unknown", "reason": "actual_not_numeric", "actual": actual}

    kind = structured.get("kind")
    if kind == "value":
        match = number == structured.get("value")
        return {
            "status": "match" if match else "out_of_range",
            "rule": structured.get("value"),
            "actual": number,
        }
    if kind == "range":
        low, high = structured.get("low"), structured.get("high")
        match = low is not None and high is not None and low <= number <= high
        return {
            "status": "match" if match else "out_of_range",
            "rule": {"low": low, "high": high},
            "actual": number,
        }
    if kind == "floor":
        low = structured.get("low")
        match = low is not None and number >= low
        return {
            "status": "match" if match else "out_of_range",
            "rule": {"floor": low},
            "actual": number,
        }
    return {"status": "unknown", "reason": "structured_kind_unhandled", "actual": number}


def _actual_dimension(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def _compare_resolutions(structured: dict[str, Any], actuals: dict[str, Any]) -> dict[str, Any]:
    width = _actual_dimension(actuals.get("width"))
    height = _actual_dimension(actuals.get("height"))
    if width is None or height is None:
        return {"status": "unknown", "reason": "actual_missing", "actual": {"width": actuals.get("width"), "height": actuals.get("height")}}

    allowed: list[dict[str, int]] = []
    for item in structured.get("items", []):
        if not isinstance(item, dict):
            continue
        item_w = _actual_dimension(item.get("width"))
        item_h = _actual_dimension(item.get("height"))
        if item_w is not None and item_h is not None:
            allowed.append({"width": item_w, "height": item_h})

    actual = {"width": width, "height": height}
    match = any(item == actual for item in allowed)
    return {
        "status": "match" if match else "out_of_set",
        "rule": allowed,
        "actual": actual,
    }


def _compare_list(structured: dict[str, Any], actual: Any) -> dict[str, Any]:
    items = [str(item).strip().lower() for item in structured.get("items", [])]
    actual_text = str(actual).strip().lower() if actual is not None else ""
    if not actual_text:
        return {"status": "unknown", "reason": "actual_missing", "actual": actual}
    match = actual_text in items
    return {
        "status": "match" if match else "out_of_set",
        "rule": structured.get("items"),
        "actual": actual,
    }


def compare_rule(rule: dict[str, Any], actuals: dict[str, Any]) -> dict[str, Any]:
    """Compare one resolved rule field against one workflow's sampler actuals.

    ``rule`` is a payload field entry from :mod:`rule_prompt` (key, status,
    value, optional structured). Returns a comparison entry. Rules the engine
    marked ``conflict``/``unknown`` are passed through without a verdict.
    """
    key = rule["key"]
    field = _field_name(key)
    if field == _RESOLUTION_FIELD:
        actual_key = "resolution"
        actual = {"width": actuals.get("width"), "height": actuals.get("height")}
    else:
        actual_key = _FIELD_TO_ACTUAL.get(field)
        actual = actuals.get(actual_key) if actual_key else None

    result: dict[str, Any] = {
        "key": key,
        "rule_status": rule.get("status"),
        "actual_key": actual_key,
        "actual": actual,
    }

    if rule.get("status") != "resolved":
        result["status"] = "unknown"
        result["reason"] = f"rule_{rule.get('status')}"
        return result
    if actual_key is None:
        result["status"] = "unknown"
        result["reason"] = "field_not_compared"
        return result
    structured = rule.get("structured")
    if structured is None:
        result["status"] = "unknown"
        result["reason"] = "rule_not_structured"
        return result

    kind = structured.get("kind")
    if kind in ("value", "range", "floor"):
        verdict = _compare_number(structured, actual)
    elif kind == "resolutions":
        verdict = _compare_resolutions(structured, actuals)
    elif kind == "list":
        verdict = _compare_list(structured, actual)
    else:
        verdict = {"status": "unknown", "reason": "structured_kind_unhandled"}
    result.update(verdict)
    return result


def compare_workflow(
    payload: dict[str, Any],
    actuals: dict[str, Any],
) -> dict[str, Any]:
    """Compare every resolved field in one prompt payload against actuals.

    ``actuals`` is the sampler params snapshot of the workflow's sampler group.
    Fields without a comparable actual, or non-numeric actuals, stay ``unknown``;
    no match is inferred from prose.
    """
    entries = [compare_rule(field, actuals) for field in payload.get("fields", [])]
    counts: dict[str, int] = {}
    for entry in entries:
        counts[entry["status"]] = counts.get(entry["status"], 0) + 1
    return {
        "status": payload.get("status"),
        "checkpoint": payload.get("checkpoint"),
        "architecture": payload.get("architecture"),
        "actuals": actuals,
        "comparisons": entries,
        "counts": counts,
    }
