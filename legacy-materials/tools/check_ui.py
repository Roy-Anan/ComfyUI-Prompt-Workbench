# -*- coding: utf-8 -*-
"""前端静态自检：app.js 里引用的 id 是否都在 index.html 里，接口是否都在服务端实现。

只在磁盘上比对，不启浏览器——用于快速拦住“id 拼错 / 接口名写错”这类低级问题。
"""

import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    html = open(os.path.join(BASE, "web", "index.html"), encoding="utf-8").read()
    js = open(os.path.join(BASE, "web", "app.js"), encoding="utf-8").read()
    server = open(os.path.join(BASE, "app", "server.py"), encoding="utf-8").read()

    html_ids = set(re.findall(r'id="([^"]+)"', html))
    js_refs = set(re.findall(r'\$\("#([^"]+)"\)', js))
    js_classes = set(re.findall(r'\$\("\.([^"]+)"\)', js))
    # app.js 里动态拼接的 HTML 也会带 id（如映射下拉），这些不算缺失
    js_built_ids = set(re.findall(r'id="([^"]+)"', js))

    html_classes = set()
    for block in re.findall(r'class="([^"]+)"', html):
        html_classes.update(block.split())

    missing_ids = sorted(js_refs - html_ids - js_built_ids)
    missing_classes = sorted(js_classes - html_classes)
    endpoints = sorted(set(re.findall(r'"/api/[a-z\-]+', js)))
    endpoints = [e.strip('"') for e in endpoints]
    missing_api = [e for e in endpoints if e not in server]

    print("index.html id 数：%d，app.js 引用 id 数：%d（其中动态生成 %d）"
          % (len(html_ids), len(js_refs), len(js_built_ids)))
    print("引用但页面没有的 id：%s" % (missing_ids or "无"))
    print("引用但页面没有的 class：%s" % (missing_classes or "无"))
    print("app.js 用到的接口：%s" % "、".join(endpoints))
    print("服务端没有实现的接口：%s" % (missing_api or "无"))

    ok = not missing_ids and not missing_classes and not missing_api
    print("结论：%s" % ("通过" if ok else "有问题"))
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
