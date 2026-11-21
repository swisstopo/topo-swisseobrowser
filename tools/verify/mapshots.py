#!/usr/bin/env python3
"""Screenshots of the map canvas, old against new page, at several zooms (the map display change of 7c5cece:
no new data tiles finer than 2.5 m/px, nearest enlargement above). Needs serve.py; headless Firefox with WebGL.
  python3 tools/verify/mapshots.py --out DIR
"""
import argparse
import os
import time

import numpy as np
from PIL import Image
from selenium import webdriver
from selenium.webdriver.firefox.options import Options


def shot(port, page, zoom, layer, out):
    o = Options()
    o.add_argument("-headless")
    d = webdriver.Firefox(options=o)
    d.set_window_size(1000, 800)
    try:
        d.get("http://127.0.0.1:%d/%s?zoom=%s&center=2645120,1249030&fromTime=2026-07-04T00:00:00.000Z&toTime=2026-07-04T23:59:59.999Z"
              "&layerId=%s&basemap=none" % (port, page, zoom, layer))
        # wait until the loading box has been hidden for 3 s
        quiet = 0
        for _ in range(240):
            hidden = d.execute_script("const e = document.querySelector('#loading'); return !e || e.hidden || getComputedStyle(e).display === 'none'")
            quiet = quiet + 1 if hidden else 0
            if quiet >= 6:
                break
            time.sleep(0.5)
        time.sleep(1)
        c = d.find_element("css selector", "#map canvas")
        c.screenshot(out)
        return d.execute_script("return window.__errs || []")
    finally:
        d.quit()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8766)
    ap.add_argument("--out", required=True)
    ap.add_argument("--zooms", default="21,22,25,26")
    ap.add_argument("--layers", default="ndvi,true")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for layer in a.layers.split(","):
        for z in a.zooms.split(","):
            f = {}
            for page in ("old", "new"):
                f[page] = os.path.join(a.out, "%s_z%s_%s.png" % (layer, z, page))
                errs = shot(a.port, page + ".html", z, layer, f[page])
                if errs:
                    print(page, z, "errors", errs)
            A = np.asarray(Image.open(f["old"]).convert("RGB")).astype(int)
            B = np.asarray(Image.open(f["new"]).convert("RGB")).astype(int)
            if A.shape != B.shape:
                print(layer, z, "size differs", A.shape, B.shape)
                continue
            dd = np.abs(A - B).max(-1)
            print(layer, "zoom", z, "pixels differing:", int((dd > 0).sum()), "of", dd.size, "| > 8 DN:", int((dd > 8).sum()),
                  "| mean |diff|:", round(float(np.abs(A - B).mean()), 3), flush=True)
            Image.fromarray(np.concatenate([A, B, np.minimum(255, dd * 8)[..., None].repeat(3, -1)], 1).astype(np.uint8)).save(
                os.path.join(a.out, "%s_z%s_old_new_diff.png" % (layer, z)))


if __name__ == "__main__":
    main()
