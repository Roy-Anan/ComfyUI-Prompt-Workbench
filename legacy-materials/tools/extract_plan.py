# -*- coding: utf-8 -*-
"""把计划书 docx 转成纯文本，便于按阶段核对。"""

import os
import re
import sys
import zipfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else \
        r"D:\WPS\WPS Cloud\WPSDrive\922741764\WPS云盘\回复.docx"
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(BASE, "logs", "计划书_全文.txt")
    with zipfile.ZipFile(path) as zf:
        xml = zf.read("word/document.xml").decode("utf-8")
    xml = xml.replace("</w:p>", "\n").replace("<w:br/>", "\n").replace("<w:tab/>", " ")
    xml = re.sub(r"<[^>]+>", "", xml)
    text = re.sub(r"\n{3,}", "\n\n", xml).strip()
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("已提取 %d 字符 -> %s" % (len(text), out))


if __name__ == "__main__":
    main()
