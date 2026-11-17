# -*- coding: utf-8 -*-
"""阶段 7：真实浏览器 UI 自检（Chrome headless + DevTools 协议）。

不依赖打包进发布包，只在开发机跑：
    python tools/ui_probe.py
它会打开 8199 上的页面，依次点开设置、备份、日志、图片预览，截图并输出
每一块的关键文本；控制台异常会作为失败项列出来。

依赖：Chrome、requests、websocket-client（开发机已装）。
"""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse

import requests
import websocket

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE, "logs")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 9333


def wait_http(url, timeout=20):
    end = time.time() + timeout
    while time.time() < end:
        try:
            return requests.get(url, timeout=1).json()
        except Exception:
            time.sleep(0.3)
    raise RuntimeError("等不到 %s" % url)


class CDP:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, timeout=15, suppress_origin=True)
        self.seq = 0
        self.events = []

    def send(self, method, params=None):
        self.seq += 1
        payload = {"id": self.seq, "method": method, "params": params or {}}
        self.ws.send(json.dumps(payload))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self.seq:
                return msg
            self.events.append(msg)

    def eval(self, expression, await_promise=False):
        res = self.send("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": await_promise,
            "userGesture": True,
        })
        result = res.get("result", {})
        if "exceptionDetails" in result:
            raise RuntimeError(result["exceptionDetails"].get("text") or "JS 异常")
        return result.get("result", {}).get("value")

    def shot(self, name):
        data = self.send("Page.captureScreenshot", {"format": "png"})["result"]["data"]
        path = os.path.join(OUT_DIR, name)
        with open(path, "wb") as fh:
            fh.write(base64.b64decode(data))
        return path

    def close(self):
        self.ws.close()


def main():
    url = "http://127.0.0.1:8199"
    if len(sys.argv) > 1:
        url = sys.argv[1]

    profile = tempfile.mkdtemp(prefix="workbench_ui_")
    proc = subprocess.Popen(
        [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
         "--remote-debugging-port=%d" % PORT, "--user-data-dir=" + profile,
         "--window-size=1400,1100", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wait_http("http://127.0.0.1:%d/json/version" % PORT)
        tab = requests.put("http://127.0.0.1:%d/json/new?%s" % (
            PORT, urllib.parse.quote(url, safe=":/?=&")), timeout=5).json()
        cdp = CDP(tab["webSocketDebuggerUrl"])
        cdp.send("Page.enable")
        cdp.send("Runtime.enable")
        cdp.send("Log.enable")
        cdp.eval("location.href=%r" % url)
        time.sleep(4)

        checks = []
        errors = []

        def check(name, ok, detail=""):
            checks.append({"name": name, "ok": bool(ok), "detail": detail})
            print(("  OK  " if ok else " FAIL ") + name + ((" · " + str(detail)) if detail else ""))

        # 首页：状态 chip / 运行条 / 会话
        chips = cdp.eval("document.querySelector('#chip-ollama').textContent")
        rt = cdp.eval("document.querySelector('#rtTask').textContent")
        check("首页状态 chip 已加载", "Ollama" in (chips or "") and "…" not in (chips or ""), chips)
        check("运行条已加载", rt is not None and "读取中" not in rt, rt)
        check("会话列表已加载", cdp.eval("document.querySelectorAll('#convlist .conv-item').length") > 0)
        home_shot = cdp.shot("UI截图_阶段7_首页.png")

        # 设置
        cdp.eval("document.querySelector('#btnSettings').click()")
        time.sleep(1.2)
        check("设置弹层打开", cdp.eval("document.querySelector('#settingsModal').hidden") is False)
        check("设置表单已填", cdp.eval("document.querySelector('#setHistory').value") not in ("", None),
              cdp.eval("document.querySelector('#setHistory').value"))
        check("系统信息有版本", "2.0" in (cdp.eval("document.querySelector('#sysVersion').textContent") or ""),
              cdp.eval("document.querySelector('#sysVersion').textContent")[:80])
        check("体检信息已渲染",
              len(cdp.eval("document.querySelector('#sysIntegrity').textContent") or "") > 8,
              cdp.eval("document.querySelector('#sysIntegrity').textContent")[:80])
        check("备份列表已渲染", cdp.eval("document.querySelectorAll('#backupList .backup-item').length") >= 1,
              cdp.eval("document.querySelector('#backupInfo').textContent"))
        settings_shot = cdp.shot("UI截图_阶段7_设置.png")

        cdp.eval("document.querySelector('#settingsTabs .stab[data-tab=backup]').click()")
        time.sleep(0.4)
        check("设置 tab 可切换",
              "active" in (cdp.eval("document.querySelector('#settingsTabs .stab[data-tab=backup]').className") or ""))
        backup_shot = cdp.shot("UI截图_阶段7_备份.png")

        cdp.eval("document.querySelector('#settingsClose').click()")
        time.sleep(0.2)
        check("设置可关闭", cdp.eval("document.querySelector('#settingsModal').hidden") is True)

        # 日志
        cdp.eval("document.querySelector('#btnLogs').click()")
        time.sleep(1.0)
        check("日志抽屉打开", cdp.eval("document.querySelector('#logsModal').hidden") is False)
        n_logs = cdp.eval("document.querySelectorAll('#logsList .log-entry').length")
        check("日志有内容", n_logs and n_logs >= 3, "条数 %s" % n_logs)
        check("日志路径显示", "workbench.log" in
              (cdp.eval("document.querySelector('#logsPath').textContent") or ""),
              cdp.eval("document.querySelector('#logsPath').textContent"))
        logs_shot = cdp.shot("UI截图_阶段7_日志.png")
        cdp.eval("document.querySelector('#logsClose').click()")

        # 图片预览
        has_img = cdp.eval("document.querySelectorAll('#gallery .gen-img').length")
        check("出图区有可预览图片", has_img and has_img > 0, "图片按钮 %s" % has_img)
        preview_shot = ""
        if has_img:
            cdp.eval("document.querySelector('#gallery .gen-img').click()")
            time.sleep(1.0)
            check("预览弹层打开", cdp.eval("document.querySelector('#previewModal').hidden") is False)
            check("预览图片有地址", cdp.eval("document.querySelector('#previewImg').src").startswith("http"),
                  cdp.eval("document.querySelector('#previewCaption').textContent"))
            check("预览参数有内容",
                  len(cdp.eval("document.querySelector('#previewMeta').textContent") or "") > 10,
                  cdp.eval("document.querySelector('#previewMeta').textContent")[:120])
            preview_shot = cdp.shot("UI截图_阶段7_预览.png")
            cdp.eval("document.querySelector('#previewClose').click()")
            time.sleep(0.2)
            check("预览可关闭", cdp.eval("document.querySelector('#previewModal').hidden") is True)

        # 错误提示条：拦截 client-log，避免把测试错误写进正式运行日志
        cdp.eval("""
          window.__oldFetch = window.fetch;
          window.fetch = (input, init) => String(input).indexOf('/api/client-log') >= 0
            ? Promise.resolve(new Response('{"ok":true}', {status: 200}))
            : window.__oldFetch(input, init);
          showError('UI 自检：错误提示条测试', '这是测试提示，不写入提示词', {where: 'ui_probe'});
        """)
        time.sleep(0.4)
        check("错误提示条显示",
              cdp.eval("document.querySelector('#errorBanner').hidden") is False,
              cdp.eval("document.querySelector('#errorText').textContent"))
        check("错误提示有 toast", cdp.eval("document.querySelectorAll('#toasts .toast.error').length") >= 1)
        error_shot = cdp.shot("UI截图_阶段7_错误提示.png")
        cdp.eval("document.querySelector('#errorClose').click(); window.fetch = window.__oldFetch;")
        time.sleep(0.2)
        check("错误提示条可关闭", cdp.eval("document.querySelector('#errorBanner').hidden") is True)

        # 控制台异常
        for ev in list(cdp.events):
            if ev.get("method") == "Runtime.exceptionThrown":
                detail = ev.get("params", {}).get("exceptionDetails", {})
                errors.append(detail.get("text") or json.dumps(detail, ensure_ascii=False)[:300])
            if ev.get("method") == "Log.entryAdded":
                entry = ev.get("params", {}).get("entry", {})
                if entry.get("level") == "error":
                    errors.append("%s: %s" % (entry.get("source"), entry.get("text")))
        check("浏览器无 JS 报错", not errors, "；".join(errors)[:400])

        payload = {
            "ok": all(c["ok"] for c in checks),
            "checks": checks,
            "errors": errors,
            "shots": [s for s in [home_shot, settings_shot, backup_shot, logs_shot,
                                   preview_shot, error_shot] if s],
        }
        out = os.path.join(OUT_DIR, "阶段7_UI自检结果.json")
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        print("结果：%d/%d 通过，截图 %d 张，明细 %s" % (
            sum(1 for c in checks if c["ok"]), len(checks), len(payload["shots"]), out))
        cdp.close()
        return 0 if payload["ok"] else 2
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
