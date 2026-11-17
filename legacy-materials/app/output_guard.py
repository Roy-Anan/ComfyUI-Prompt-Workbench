# -*- coding: utf-8 -*-
"""输出失控检测。

本地 8B 量化模型在长负面清单上会“词汇接龙”（drawing, painting, hp printer artifacts…），
表现为篇幅暴涨、逗号数量异常、同一短语反复。这里只做判定，不改写模型输出。
"""

import re

MAX_CHARS = 5200          # 六段结构正常在 1500~3000 字符
MAX_COMMAS = 180          # 正常 Negative 40 标签 + 正向描述，逗号远低于此
MAX_SAME_PHRASE = 3       # 同一英文短语连续出现次数


def _phrase_repeat(text):
    words = re.findall(r"[A-Za-z][A-Za-z\-']+", text.lower())
    grams = [" ".join(words[i:i + 3]) for i in range(len(words) - 2)]
    best, cur = 1, 1
    for i in range(1, len(grams)):
        if grams[i] == grams[i - 1]:
            cur += 1
            best = max(best, cur)
        else:
            cur = 1
    return best


def analyse(text):
    reasons = []
    if len(text) > MAX_CHARS:
        reasons.append("篇幅 %d 字符，超过 %d" % (len(text), MAX_CHARS))
    commas = text.count(",") + text.count("，")
    if commas > MAX_COMMAS:
        reasons.append("逗号 %d 个，疑似清单接龙" % commas)
    if _phrase_repeat(text) > MAX_SAME_PHRASE:
        reasons.append("同一短语连续重复")
    return {"ok": not reasons, "reasons": reasons, "chars": len(text), "commas": commas}


RETRY_NOTE = ("\n\n（上一次输出失控了。请只输出六段，每段一次；Positive 一小段自然语言；"
              "Negative 不超过 40 个标签；【模型适配说明】不超过 3 句；"
              "禁止罗列成串的名词或动词，写完立即停止。）")
