#!/usr/bin/env python3
"""Serves the repository for the layer verification, with three copies of the page:

  /new.html           the page of the working tree
  /old.html           the page of a reference commit (--old, default 7c5cece^: before the tile-pipeline changes)
  /new-noworker.html  the working tree page with the decode workers off (main-thread decoding, as under file://)

Each copy gets a hook script appended to its module: window.__t exposes the page's own functions
(renderTile, sampleAoi, readGrid, resolveScenes, ...) so tools/verify/drive.py can call them. The page files
on disk are not changed. Usage: python3 tools/verify/serve.py [--port 8766] [--old <commit>]
"""
import argparse
import http.server
import os
import re
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PAGE = "swisseo-browser.html"
HOOK = os.path.join(os.path.dirname(__file__), "hook.js")

# identifiers of the page exposed to the test (only those declared at the top level of the page are used)
NAMES = ["LAYER", "SOURCES", "creditText", "layerAttr", "defaults", "resolveScenes", "resolveRef", "renderTile", "sampleAoi", "statRec", "readGrid",
         "readGridBands", "readPoint", "winDiff", "windowItems", "vhiSeason", "readVegMask", "assetUrl", "prodUrl", "vhiUrl",
         "vegUrl", "vegParse", "habitatOf", "fdcModel", "fdcPredict", "fdcInput", "cloudOf", "loadMonth", "coversNow",
         "sceneBox", "MISSING_RGB", "CHANGE_RGB", "NOCHANGE_RGB", "SHADOW_RGB", "FDC_PALETTE", "BASE_GAIN", "BASE_GAMMA",
         "OPT", "ILLUM_THR", "EDGE_M", "EDGE_DARK", "MASK_DEFAULTS", "DATA_MAXZOOM", "DECODE_WORKERS", "decodePool"]


def declared(src, name):
    """Declared at the top level: a function, or a const / let / var line that assigns it (also "const A = 1, B = 2")."""
    n = re.escape(name)
    return re.search(r"^(?:async function|function)\s+" + n + r"\b", src, re.M) is not None or \
        re.search(r"^(?:const|let|var)\s+(?:[^\n]*,\s*)?" + n + r"\s*=", src, re.M) is not None


def instrument(src, noworker=False):
    if noworker:
        src, n = re.subn(r"^const DECODE_WORKERS = .*?, DECODE_TIMEOUT", "const DECODE_WORKERS = 0, DECODE_TIMEOUT", src, count=1, flags=re.M)
        if n != 1:
            raise SystemExit("DECODE_WORKERS not found")
        # with 0 workers decodePool decodes on the main thread (its fallback)
    ramps = sorted(set(re.findall(r"^(?:const|let) ((?:R|P|STEPS)_[A-Z0-9_]+)\b", src, re.M)))
    names = [n for n in NAMES if declared(src, n)] + ramps
    getters = ",\n".join('  get %s() { return %s; }' % (n, n) for n in names)
    hook = open(HOOK, encoding="utf8").read().replace("/*GETTERS*/", getters).replace("/*RAMPS*/", repr(ramps).replace("'", '"'))
    i = src.rindex("</script>")
    src = src[:i] + "\n/* verification hook (tools/verify/serve.py) */\n" + hook + "\n" + src[i:]
    # errors of the page (also a module that fails to compile) are kept in window.__errs for the driver
    catcher = ('<script>window.__errs = []; addEventListener("error", e => window.__errs.push(String(e.message) + " @" + e.lineno));'
               'addEventListener("unhandledrejection", e => window.__errs.push("rejection: " + String(e.reason && e.reason.stack || e.reason)));</script>')
    j = src.index("<head>") + len("<head>")
    return src[:j] + catcher + src[j:]


class Handler(http.server.SimpleHTTPRequestHandler):
    pages = {}

    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in self.pages:
            body = self.pages[path]().encode("utf8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def log_message(self, *a):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8766)
    ap.add_argument("--old", default="7c5cece^")
    a = ap.parse_args()
    old = subprocess.run(["git", "-C", ROOT, "show", a.old + ":" + PAGE], capture_output=True, text=True, check=True).stdout
    cur = lambda: open(os.path.join(ROOT, PAGE), encoding="utf8").read()
    Handler.pages = {"/new.html": lambda: instrument(cur()), "/old.html": lambda: instrument(old),
                     "/new-noworker.html": lambda: instrument(cur(), noworker=True)}
    print("serving %s on http://127.0.0.1:%d (old = %s)" % (ROOT, a.port, a.old), flush=True)
    http.server.ThreadingHTTPServer(("127.0.0.1", a.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
