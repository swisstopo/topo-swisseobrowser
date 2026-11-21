#!/usr/bin/env python3
"""Checks of the layers compare.py leaves out:

  fdc   Forest Disturbance Classification: the band values read with rasterio (first scene with data wins, masks as
        the page) are classified by the ORIGINAL Sentinel Hub script (pinned commit 0a071cf) in QuickJS, and compared
        with the classes the page computed (sampleAoi) and drew (renderTile).
  vhi   swissEO VHI forest / vegetation: the COG values the page reads (readGrid) against rasterio, and the colours of
        the WMS map against the VHI classes of the same pixels.

  python3 tools/verify/special.py --web DIR [--tiles A10,...]
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import urllib.request

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import ref  # noqa: E402

FDC_SCRIPT = ("https://raw.githubusercontent.com/sentinel-hub/custom-scripts/0a071cfc15adc91ae79cdda1cec6332133bb7565/"
              "sentinel-2/forest_disturbance_classification/script.js")
FDC_BANDS = ["b02", "b05", "b06", "b8a", "b11", "b12"]


def fdc_original(vectors):
    """Classes of the original script for an N x 6 array of DN (already max(0, DN - 1000))."""
    src = urllib.request.urlopen(FDC_SCRIPT, timeout=60).read().decode("utf8")
    a, b = src.index("function pt0("), src.index("function predict(")
    trees = src[a:b]
    # predict() of the script, verbatim except that eval(`pt${i}`) becomes a lookup of the same functions
    pred = src[b:]
    pred = pred.replace("eval(`pt${0+i}(B02, B05, B06, B8A, B11, B12)`)", "PT[i](B02, B05, B06, B8A, B11, B12)")
    if "PT[i]" not in pred:
        raise SystemExit("unexpected predict() in the original script")
    with tempfile.TemporaryDirectory() as d:
        np.savetxt(os.path.join(d, "v.txt"), vectors, fmt="%d")
        js = os.path.join(d, "run.js")
        open(js, "w").write(trees + "\nconst PT = [" + ",".join("pt%d" % i for i in range(150)) + "];\n" + pred + """
const lines = std.loadFile(scriptArgs[1]).trim().split("\\n"), out = [];
for (const l of lines) { const v = l.split(" ").map(Number); out.push(predict(v[0], v[1], v[2], v[3], v[4], v[5])); }
std.out.puts(out.join("\\n"));
""")
        r = subprocess.run(["qjs", "--std", js, os.path.join(d, "v.txt")], capture_output=True, text=True, check=True)
    return np.array([int(x) for x in r.stdout.split()], np.int16)


def fdc_ref(meta, s, scenes, bbox, W, H):
    """Classes as sampleAoi computes them (first scene with data wins, masks), the class by the original script."""
    cls = np.full((H, W), -1, np.int16)
    done = np.zeros((H, W), bool)
    if ref.veg_on(s["veg"]):
        done |= ref.veg_mask(s["veg"], scenes[0][:10], bbox, W, H) == 0
    tout = ref.terr_out(s)
    vec = np.zeros((H, W, 6), np.int64)
    todo = np.zeros((H, W), bool)
    for sid in scenes:
        a = [ref.read_grid(ref.asset_url(sid, b), bbox, W, H, 0) for b in FDC_BANDS]
        if any(x is None for x in a):
            continue
        a = [x[0] for x in a]
        has = ~done & (a[0] != 0)
        m = np.zeros((H, W), bool)
        if s["cloud"] or s["shadow"]:
            cm = ref.read_grid(ref.asset_url(sid, "cloud"), bbox, W, H, 0)[0]
            m |= (bool(s["cloud"]) & ((cm == 1) | (cm == 2))) | (bool(s["shadow"]) & (cm == 3))
        if tout:
            m |= tout(ref.read_grid(ref.asset_url(sid, "terrain"), bbox, W, H, 255)[0])
        m &= has
        done |= m
        has &= ~m
        ok = has.copy()
        for x in a:
            ok &= x != 0
        for i in range(6):
            vec[..., i] = np.where(ok, np.maximum(0, a[i].astype(np.int64) - 1000), vec[..., i])
        todo |= ok
        done |= ok
    v = vec[todo]
    uniq, inv = np.unique(v, axis=0, return_inverse=True)
    pc = fdc_original(uniq)
    cls[todo] = pc[inv.ravel()]
    return cls, len(uniq)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--web", required=True)
    ap.add_argument("--tiles", default="A10,B10,L10")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    meta = json.load(open(os.path.join(a.web, "new", "meta.json")))
    meta["L"] = {l["id"]: l for l in meta["layers"]}
    out_path = a.out or os.path.join(os.path.dirname(a.web.rstrip("/")), "special.json")
    res = json.load(open(out_path)) if os.path.exists(out_path) else {}
    pal = meta["consts"]["FDC_PALETTE"]
    for tile in a.tiles.split(","):
        tdir = os.path.join(a.web, "new", tile)
        info = json.load(open(os.path.join(tdir, "info.json")))
        bbox = info["bbox"]
        for masks in ("def", "off"):
            key = "fdc_" + masks
            rec = info["layers"].get(key)
            if not rec or tile + "/" + key in res:
                continue
            s = ref.settings(meta, "fdc", masks)
            cls, nu = fdc_ref(meta, s, rec["scenes"], bbox, 512, 512)
            web = np.load(os.path.join(tdir, "cls_%s.npy" % key))
            tilew = np.load(os.path.join(tdir, "tile_%s.npy" % key)) if os.path.exists(os.path.join(tdir, "tile_%s.npy" % key)) else None
            r = dict(n=int((cls >= 0).sum()), unique_vectors=int(nu), class_mismatch=int((cls != web).sum()),
                     counts_ref={int(k): int(v) for k, v in zip(*np.unique(cls[cls >= 0], return_counts=True))},
                     counts_web={int(k): int(v) for k, v in zip(*np.unique(web[web >= 0], return_counts=True))})
            if tilew is not None:
                # colours of the map: palette of the class, healthy (2) not drawn; the map fills a pixel from the next scene
                # when the first scene gives "healthy", so only the pixels classified in the first pass are compared
                exp = np.zeros((512, 512, 4), np.uint8)
                for k, e in pal.items():
                    if e[1]:
                        m = cls == int(k)
                        exp[m, :3] = e[1]
                        exp[m, 3] = 255
                both = (exp[..., 3] > 0)
                r["tile_colour_mismatch_on_drawn"] = int((tilew[both] != exp[both]).any(-1).sum())
                r["tile_drawn_web"], r["tile_drawn_ref"] = int((tilew[..., 3] > 0).sum()), int(both.sum())
            res[tile + "/" + key] = r
            json.dump(res, open(out_path, "w"), indent=1)
            print(tile, key, r, flush=True)


if __name__ == "__main__" and "--vhi" not in sys.argv:
    main()


VHI_COLOURS = [(0, 9, 0xb56a29), (10, 19, 0xce8540), (20, 29, 0xf5cd85), (30, 39, 0xfff5ba), (40, 49, 0xcbffca),
               (50, 59, 0x52bd9f), (60, 100, 0x0470b0), (110, 110, 0xb3b6b7)]


def vhi_check(web, tiles, port=8766):
    """The VHI COG as the page reads it (readGrid in the browser) against rasterio, and the WMS map colours against the
    VHI classes of the COG values at the same pixels."""
    import io
    from PIL import Image
    import drive
    d = drive.open_page(port, "new.html", "2026-07-04")
    out = {}
    try:
        for tile in tiles:
            info = json.load(open(os.path.join(web, "new", tile, "info.json")))
            bbox = info["bbox"]
            for lid, kind, wms in (("vhi", "forest", "ch.swisstopo.swisseo_vhi_v100"),
                                   ("vhiveg", "vegetation", "ch.swisstopo.swisseo_vhi_v100_vegetation")):
                rec = info["layers"].get(lid + "_def")
                if not rec or not rec.get("scenes"):
                    continue
                sid = rec["scenes"][0]
                url = ref.vhi_url(sid, kind)
                w = drive.call(d, "raw", url, bbox, 512, 512, 255)
                web_v = drive.dec(w["band"], np.float32, (512, 512))
                rv = ref.read_grid(url, bbox, 512, 512, 255)[0]
                r = dict(item=sid, cog=url.split("/")[-1], values_identical=bool(np.array_equal(web_v, rv)),
                         n_valid=int((rv <= 100).sum()), n_110=int((rv == 110).sum()))
                # the WMS image the map draws (same request as renderWmsCanvas), compared at native 10 m
                if info["res"] == 10.0:
                    q = ("https://wms.geo.admin.ch/?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image%2Fpng&TRANSPARENT=true"
                         "&LAYERS=" + wms + "&STYLES=&CRS=EPSG%3A2056&BBOX=" + ",".join("%.2f" % v for v in bbox) +
                         "&WIDTH=512&HEIGHT=512&item=" + sid + "&lang=en")
                    im = np.array(Image.open(io.BytesIO(urllib.request.urlopen(q, timeout=120).read())).convert("RGBA"))
                    exp = np.zeros((512, 512, 3), np.int32)
                    has = np.zeros((512, 512), bool)
                    for lo, hi, c in VHI_COLOURS:
                        m = (rv >= lo) & (rv <= hi)
                        exp[m] = [(c >> 16) & 255, (c >> 8) & 255, c & 255]
                        has |= m
                    drawn = im[..., 3] > 0
                    both = has & drawn
                    dist = np.abs(im[..., :3].astype(int) - exp).max(-1)
                    r.update(wms_drawn=int(drawn.sum()), cog_with_class=int(has.sum()),
                             wms_drawn_without_value=int((drawn & ~has).sum()), value_not_drawn=int((has & ~drawn).sum()),
                             colour_match=int((both & (dist <= 2)).sum()), colour_mismatch=int((both & (dist > 2)).sum()))
                out[tile + "/" + lid] = r
                print(tile, lid, r, flush=True)
    finally:
        d.quit()
    return out


if __name__ == "__main__" and "--vhi" in sys.argv:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vhi", action="store_true")
    ap.add_argument("--web", required=True)
    ap.add_argument("--tiles", default="A10,A40,L10")
    a = ap.parse_args()
    res = vhi_check(a.web, a.tiles.split(","))
    json.dump(res, open(os.path.join(os.path.dirname(a.web.rstrip("/")), "vhi.json"), "w"), indent=1)
