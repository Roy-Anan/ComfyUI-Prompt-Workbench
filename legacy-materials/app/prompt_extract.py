# -*- coding: utf-8 -*-
"""从助手回复里抽出正/负提示词与参数段。

只做切分和去包裹（```text 围栏、反引号），不改写内容——提示词记录要能和原回复逐字对照。
"""

import re

HEADINGS = [
    ("model", ["【当前模型】", "【Current Model】"]),
    ("positive", ["【Positive Prompt】", "【Positive 提示词】"]),
    ("negative", ["【Negative Prompt】", "【Negative 提示词】"]),
    ("settings", ["【Generation Settings】", "【生成设置】", "【参数设置】"]),
    ("adapt", ["【模型适配说明】", "【Model Adaptability Explanation】"]),
    ("pending", ["【待确认项】", "【Pending Confirmation Items】"]),
]


def _find_heading(text, aliases, start=0):
    best = None
    for alias in aliases:
        idx = text.find(alias, start)
        if idx >= 0 and (best is None or idx < best):
            best = idx
    return best


def strip_wrapper(block):
    """去掉代码围栏/反引号包裹与首尾空白。"""
    text = block.strip()
    text = re.sub(r"^```[A-Za-z]*\s*", "", text)
    text = re.sub(r"```$", "", text)
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln and ln not in ("```text", "```")]
    cleaned = "\n".join(lines).strip()
    cleaned = cleaned.strip("`").strip()
    return cleaned


def extract(text):
    """返回 {model, positive, negative, settings, adapt, pending}，缺失为 ''。"""
    result = {key: "" for key, _ in HEADINGS}
    if not text:
        return result

    positions = []
    for key, aliases in HEADINGS:
        idx = _find_heading(text, aliases)
        if idx is not None:
            positions.append((idx, key, aliases))
    positions.sort()

    for i, (idx, key, aliases) in enumerate(positions):
        for alias in aliases:
            if text.startswith(alias, idx):
                start = idx + len(alias)
                break
        else:
            start = idx
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        result[key] = strip_wrapper(text[start:end])
    return result
