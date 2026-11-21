#!/usr/bin/env python3
"""Compares the web results of drive.py: page versions with each other (regression) and with the rasterio reference.

  python3 tools/verify/compare.py --web DIR [--layers ...] [--tiles ...] [--skip-ref]
Writes DIR/../compare.json and prints a table.
"""
import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import ref  # noqa: E402

SPECIAL = {"fnclass", "wms"}   # checked by tools/verify/special.py


def load(web, page, tile, kind, key):
    p = os.path.join(web, page, tile, "%s_%s.npy" % (kind, key))
    return np.load(p) if os.path.exists(p) else None


def rgba_diff(a, b):
    if a is None or b is None:
        return None if a is None and b is None else "missing:%s" % ("web" if a is None else "ref")
    d = np.abs(a.astype(int) - b.astype(int))
    alpha = int(((a[..., 3] > 0) != (b[..., 3] > 0)).sum())
    both = (a[..., 3] > 0) & (b[..., 3] > 0)
    dd = d[both][:, :3]
    return dict(alpha=alpha, n=int(both.sum()), max=int(dd.max()) if dd.size else 0, n_gt1=int((dd.max(1) > 1).sum()) if dd.size else 0,
                n_ne=int((dd.max(1) > 0).sum()) if dd.size else 0)


def val_diff(a, b):
    if a is None or b is None:
        return None if a is None and b is None else "missing:%s" % ("web" if a is None else "ref")
    a, b = a.astype(np.float64), b.astype(np.float64)
    na, nb = np.isnan(a), np.isnan(b)
    both = ~na & ~nb
    d = np.abs(a - b)[both]
    return dict(nan_mismatch=int((na != nb).sum()), n=int(both.sum()), max=float(d.max()) if d.size else 0.0,
                n_gt=int((d > 1e-6).sum()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--web", required=True)
    ap.add_argument("--layers", default="")
    ap.add_argument("--tiles", default="")
    ap.add_argument("--masks", default="def,off")
    ap.add_argument("--skip-ref", action="store_true")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    meta = json.load(open(os.path.join(a.web, "new", "meta.json")))
    meta["L"] = {l["id"]: l for l in meta["layers"]}
    # numeric constants the hook could not export: read them from the page source
    import re
    page = open(os.path.join(os.path.dirname(__file__), "..", "..", "swisseo-browser.html"), encoding="utf8").read()
    for k, v in list(meta["consts"].items()):
        if v is None:
            m = re.search(r"\b" + k + r"\s*=\s*([-0-9.]+)", page)
            if m:
                meta["consts"][k] = float(m.group(1))
    out_path = a.out or os.path.join(os.path.dirname(a.web.rstrip("/")), "compare.json")
    res = json.load(open(out_path)) if os.path.exists(out_path) else {}
    tiles = a.tiles.split(",") if a.tiles else sorted(os.listdir(os.path.join(a.web, "new")))
    tiles = [t for t in tiles if os.path.isdir(os.path.join(a.web, "new", t))]
    for tile in tiles:
        info = json.load(open(os.path.join(a.web, "new", tile, "info.json")))
        bbox, W = info["bbox"], 512
        ids = a.layers.split(",") if a.layers else list(meta["L"])
        for lid in ids:
            L = meta["L"][lid]
            for masks in a.masks.split(","):
                key = lid + "_" + masks
                if key not in info["layers"]:
                    continue
                rk = tile + "/" + key
                r = res.get(rk, {})
                rec = info["layers"][key]
                r["scenes"] = rec.get("scenes")
                r["errors"] = {k: rec[k] for k in ("tileError", "valuesError") if k in rec}
                # regression: old and no-worker against new, bit for bit
                for other in ("old", "new-noworker"):
                    for kind, f in (("tile", rgba_diff), ("vals", val_diff), ("cls", val_diff)):
                        A, B = load(a.web, "new", tile, kind, key), load(a.web, other, tile, kind, key)
                        if A is None and B is None:
                            continue
                        if A is not None and B is not None and A.shape == B.shape and np.array_equal(A, B, equal_nan=(kind == "vals")):
                            r["%s_%s" % (other, kind)] = "identical"
                        else:
                            r["%s_%s" % (other, kind)] = f(A, B)
                # reference
                if not a.skip_ref and L["type"] not in SPECIAL and rec.get("scenes") is not None and "ref_tile" not in r:
                    s = ref.settings(meta, lid, masks)
                    scenes = rec["scenes"]
                    t0 = time.time()
                    try:
                        r["ref_scenes_ok"] = (scenes == ref.s2_scenes(info["date"])) if L["source"] == "s2" and L["type"] != "wincomp" else None
                        why = None
                        if L["type"] == "diff2":
                            sel = ref.ref_selection(info["date"])
                            r["ref_refscenes_ok"] = sel["scenes"] == rec.get("refScenes")
                            img, dif = ref.diff2_tile(meta, lid, s, info["date"], scenes, sel["scenes"], bbox, W, W)
                            # the TIFF-32 / statistics path: the index of each date as sampleAoi computes it
                            fn = lambda v, ss, f=ref.FN[lid]: f(v, s)
                            va = ref.sample(meta, lid, s, scenes, bbox, W, W)
                            vb = ref.sample(meta, lid, s, sel["scenes"], bbox, W, W)
                            v = (va.astype(np.float64) - vb.astype(np.float64)).astype(np.float32)
                            r["ref_vals"] = val_diff(load(a.web, "new", tile, "vals", key), v)
                            # map (dateIndex: a masked pixel is taken from the next scene) vs download (sampleAoi: stays masked)
                            r["map_vs_download"] = val_diff(dif, v)
                            np.save(os.path.join(a.web, "new", tile, "refvals_%s.npy" % key), v)
                        elif L["type"] == "wincomp":
                            img, dif, ref_ids = ref.wincomp(meta, lid, s, info["date"], scenes, bbox, W, W)
                            r["ref_scenes_ok"] = scenes == ref.window_ids(info["date"], s.get("days", 30))
                            r["ref_vals"] = val_diff(load(a.web, "new", tile, "vals", key), dif)
                            np.save(os.path.join(a.web, "new", tile, "refvals_%s.npy" % key), dif)
                        elif L["type"] == "vhiseason":
                            img, v, sr = ref.season_tile(meta, lid, s, scenes, bbox, W, W)
                            r["ref_vals"] = val_diff(load(a.web, "new", tile, "vals", key), v)
                            r["season_days"] = len(sr["ids"])
                            np.save(os.path.join(a.web, "new", tile, "refvals_%s.npy" % key), v)
                        else:
                            img, why = ref.render_tile(meta, lid, s, scenes, bbox, W, W)
                        r["ref_tile"] = rgba_diff(load(a.web, "new", tile, "tile", key), img) if why is None else why
                        if L["type"] in ("index", "cont", "terrain", "fnrgb") or L["type"] == "class":
                            v = ref.sample(meta, lid, s, scenes, bbox, W, W)
                            kind = "cls" if L["type"] == "class" else "vals"
                            r["ref_" + kind] = val_diff(load(a.web, "new", tile, kind, key), v)
                            np.save(os.path.join(a.web, "new", tile, "ref%s_%s.npy" % (kind, key)), v)
                        if img is not None:
                            np.save(os.path.join(a.web, "new", tile, "reftile_%s.npy" % key), img)
                    except Exception as e:  # noqa: BLE001
                        r["ref_error"] = repr(e)[:300]
                    r["ref_sec"] = round(time.time() - t0, 1)
                res[rk] = r
                json.dump(res, open(out_path, "w"), indent=1)
                print(rk, {k: v for k, v in r.items() if k != "scenes"}, flush=True)


if __name__ == "__main__":
    main()
