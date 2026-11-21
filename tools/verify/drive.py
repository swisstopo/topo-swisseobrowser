#!/usr/bin/env python3
"""Runs the page's own rendering and value functions in headless Firefox and stores the results as .npy files.

Needs tools/verify/serve.py running. For each page version (new, old, new-noworker), test tile and layer it stores:
  tile_<layer>_<masks>.npy    RGBA of renderTile (the map tile), uint8 H x W x 4
  vals_<layer>_<masks>.npy    the values (sampleAoi / winDiff, as the TIFF-32 download), float32 H x W
  cls_<layer>_<masks>.npy     the classes of class layers (sampleAoi), int16 H x W
and a JSON file with the scenes and timings. Usage:
  python3 tools/verify/drive.py --out DIR [--pages new,old,new-noworker] [--layers ndvi,true] [--tiles A10,A40]
"""
import argparse
import base64
import json
import os
import sys
import time

import numpy as np
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

ORIGIN = (2420000.0, 1350000.0)
# test tiles: quad-tree tiles of the map (2560 m/px / 2^z, 512 px) around a point, on a date
TILES = {
    "A10":   dict(z=8,  at=(2645000, 1249000), date="2026-07-04"),   # Aarau, native 10 m, clear, two orbits
    "A20":   dict(z=7,  at=(2645000, 1249000), date="2026-07-04"),   # 20 m overview
    "A40":   dict(z=6,  at=(2645000, 1249000), date="2026-07-04"),   # 40 m overview
    "A2":    dict(z=10, at=(2645000, 1249000), date="2026-07-04"),   # 2.5 m, the finest map tile
    "B10":   dict(z=8,  at=(2645000, 1249000), date="2026-08-30"),   # Aarau, cloudy, two orbits: the masks
    "L10":   dict(z=8,  at=(2658500, 1237000), date="2026-07-04"),   # Hallwilersee: water
    "S10":   dict(z=8,  at=(2645000, 1143000), date="2026-08-13"),   # Aletsch: snow, ice, terrain shadow
}
VALUE_TYPES = {"index", "cont", "terrain", "fnrgb", "diff2", "vhiseason", "wincomp"}


def tile_box(z, at):
    res = 2560.0 / 2 ** z
    span = 512 * res
    tx, ty = int((at[0] - ORIGIN[0]) // span), int((ORIGIN[1] - at[1]) // span)
    x0, y1 = ORIGIN[0] + tx * span, ORIGIN[1] - ty * span
    return [x0, y1 - span, x0 + span, y1], res


def call(d, fn, *args):
    js = ("const cb = arguments[arguments.length - 1];"
          "window.__t[arguments[0]](...arguments[1]).then(r => cb(r), e => cb({ error: String(e && e.stack || e) }));")
    return d.execute_async_script(js, fn, list(args))


def dec(s, dtype, shape=None):
    if s is None:
        return None
    a = np.frombuffer(base64.b64decode(s), dtype=dtype)
    return a.reshape(shape) if shape else a


def open_page(port, page, date):
    o = Options()
    o.add_argument("-headless")
    d = webdriver.Firefox(options=o)
    d.set_window_size(1400, 900)
    d.set_script_timeout(1800)
    d.get("http://127.0.0.1:%d/%s?zoom=17&center=2645000,1249000&fromTime=%sT00:00:00.000Z&toTime=%sT23:59:59.999Z&layerId=true&showLayer=false"
          % (port, page, date, date))
    for _ in range(120):
        if d.execute_script("return !!(window.__t && window.__t.T && window.__t.T.LAYER)"):
            return d
        time.sleep(1)
    raise SystemExit("hook not found on " + page)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8766)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pages", default="new,old,new-noworker")
    ap.add_argument("--layers", default="")
    ap.add_argument("--tiles", default=",".join(TILES))
    ap.add_argument("--masks", default="def,off")
    a = ap.parse_args()
    for page in a.pages.split(","):
        d = open_page(a.port, page + ".html", "2026-08-31")
        meta = d.execute_script("return window.__t.meta()")
        pdir = os.path.join(a.out, page)
        os.makedirs(pdir, exist_ok=True)
        json.dump(meta, open(os.path.join(pdir, "meta.json"), "w"), indent=1)
        layers = {l["id"]: l for l in meta["layers"]}
        ids = a.layers.split(",") if a.layers else list(layers)
        for tname in a.tiles.split(","):
            t = TILES[tname]
            bbox, res = tile_box(t["z"], t["at"])
            tdir = os.path.join(pdir, tname)
            os.makedirs(tdir, exist_ok=True)
            info = {"bbox": bbox, "res": res, "date": t["date"], "layers": {}}
            ipath = os.path.join(tdir, "info.json")
            if os.path.exists(ipath):
                info = json.load(open(ipath))
            for lid in ids:
                lt = layers[lid]["type"]
                for masks in a.masks.split(","):
                    key = lid + "_" + masks
                    if key in info["layers"]:
                        continue
                    t0 = time.time()
                    rec = {}
                    r = call(d, "tile", lid, t["date"], masks, bbox, 512, 512)
                    if "error" in r:
                        rec["tileError"] = r["error"][:400]
                    else:
                        rec.update(scenes=r["scenes"], tileMs=r["ms"])
                        if r["rgba"]:
                            np.save(os.path.join(tdir, "tile_%s.npy" % key), dec(r["rgba"], np.uint8, (512, 512, 4)))
                    if lt in VALUE_TYPES or lt in ("class", "fnclass"):
                        v = call(d, "values", lid, t["date"], masks, bbox, 512, 512)
                        if "error" in v:
                            rec["valuesError"] = v["error"][:400]
                        else:
                            rec.update(refScenes=v.get("refScenes"), masked=v.get("masked"), shadow=v.get("shadow"), outside=v.get("outside"))
                            if v.get("vals"):
                                np.save(os.path.join(tdir, "vals_%s.npy" % key), dec(v["vals"], np.float32, (512, 512)))
                            if v.get("cls"):
                                np.save(os.path.join(tdir, "cls_%s.npy" % key), dec(v["cls"], np.int16, (512, 512)))
                    rec["sec"] = round(time.time() - t0, 1)
                    info["layers"][key] = rec
                    json.dump(info, open(ipath, "w"), indent=1)
                    print(page, tname, key, rec.get("sec"), "s", rec.get("tileError", "")[:80], rec.get("valuesError", "")[:80], flush=True)
        d.quit()


if __name__ == "__main__":
    sys.exit(main())
