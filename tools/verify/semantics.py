#!/usr/bin/env python3
"""Does each layer show what its description says? Statistics of the web values (drive.py, masks off) per land
cover, with the Sen2Cor scene classification (SCL 4 vegetation, 5 bare soil, 6 water, 11 snow / ice) of the same
scene and the forest mask of swissEO VHI v100 (habitat map) as independent classes.

  python3 tools/verify/semantics.py --web DIR
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import ref  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--web", required=True)
    a = ap.parse_args()
    W = os.path.join(a.web, "new")
    ld = lambda t, k: np.load(os.path.join(W, t, k + ".npy")) if os.path.exists(os.path.join(W, t, k + ".npy")) else None
    info = {t: json.load(open(os.path.join(W, t, "info.json"))) for t in os.listdir(W) if os.path.isdir(os.path.join(W, t))}
    out, checks = {}, []

    def cls_masks(t):
        scl = ld(t, "cls_scl_off")
        i = info[t]
        forest = ref.veg_mask("forest", i["date"], i["bbox"], 512, 512) == 1
        return scl, forest

    def q(v, m, p=50):
        x = v[m & np.isfinite(v)]
        return float(np.percentile(x, p)) if x.size else float("nan"), int(x.size)

    def check(name, ok, detail):
        checks.append(dict(check=name, ok=bool(ok), detail=detail))
        print(("PASS " if ok else "FAIL ") + name + ": " + detail, flush=True)

    # Aarau (A10, clear day) and Hallwilersee (L10)
    for t in ("A10", "L10"):
        scl, forest = cls_masks(t)
        veg, bare, water = scl == 4, scl == 5, scl == 6
        out[t] = {"n_forest": int(forest.sum()), "n_veg": int(veg.sum()), "n_bare": int(bare.sum()), "n_water": int(water.sum())}
        ndvi = ld(t, "vals_ndvi_off")
        m, n = q(ndvi, forest)
        check(t + " NDVI forest > 0.6 (dense vegetation)", m > 0.6, "median %.3f over %d forest pixels" % (m, n))
        if water.sum() > 100:
            m, n = q(ndvi, water)
            check(t + " NDVI water < 0", m < 0, "median %.3f over %d water pixels" % (m, n))
            m, n = q(ld(t, "vals_ndwi_off"), water)
            check(t + " NDWI water > 0.3 (open water)", m > 0.3, "median %.3f over %d water pixels" % (m, n))
        m, n = q(ld(t, "vals_ndwi_off"), forest)
        check(t + " NDWI forest < 0", m < 0, "median %.3f over %d forest pixels" % (m, n))
        if bare.sum() > 100:
            mf, _ = q(ld(t, "vals_ndmi_off"), forest)
            mb, nb = q(ld(t, "vals_ndmi_off"), bare)
            check(t + " NDMI forest > bare soil (more moisture in vegetation)", mf > mb, "forest %.3f, bare %.3f (%d px)" % (mf, mb, nb))
            mb2, _ = q(ld(t, "vals_barren_off"), bare)
            mf2, _ = q(ld(t, "vals_barren_off"), forest)
            check(t + " Barren Soil BSI bare > forest", mb2 > mf2, "BSI bare %.3f, forest %.3f" % (mb2, mf2))
            tile = ld(t, "tile_barren_off").astype(int)
            rb = float(np.mean(tile[bare][:, 0] - tile[bare][:, 1]))
            rf = float(np.mean(tile[forest][:, 1] - tile[forest][:, 0]))
            check(t + " Barren Soil colours: bare red, vegetation green", rb > 0 and rf > 0,
                  "bare: mean R − G %.1f; forest: mean G − R %.1f" % (rb, rf))
        lo, n = q(ld(t, "vals_evi_off"), veg, 10)
        hi, _ = q(ld(t, "vals_evi_off"), veg, 90)
        check(t + " EVI vegetation 0.2 to 0.8 (P10–P90)", lo >= 0.2 - 0.05 and hi <= 0.8 + 0.1, "P10 %.3f, P90 %.3f (%d px)" % (lo, hi, n))
        lo, n = q(ld(t, "vals_ndre_off"), veg, 10)
        hi, _ = q(ld(t, "vals_ndre_off"), veg, 90)
        check(t + " NDRE crops / vegetation about 0.2 to 0.6", lo > 0.1 and hi < 0.7, "P10 %.3f, P90 %.3f" % (lo, hi))
        m, _ = q(ld(t, "vals_savi_off"), veg)
        mn, _ = q(ndvi, veg)
        check(t + " SAVI below NDVI on vegetation (soil adjustment)", m < mn, "SAVI %.3f, NDVI %.3f" % (m, mn))
        m, _ = q(ld(t, "vals_mtvi2_off"), veg)
        check(t + " MTVI2 vegetation in 0…1", 0 < m < 1, "median %.3f" % m)
        m, _ = q(ld(t, "vals_nbr_off"), forest)
        check(t + " NBR forest high (> 0.4, unburned)", m > 0.4, "median %.3f" % m)
        nddi, ndwi_s = ld(t, "vals_nddi_off"), None
        # NDDI uses NDWI = (B08 − B11)/(B08 + B11): drier (lower NDWI) gives a higher NDDI at similar NDVI
        nd = ld(t, "vals_ndmi_off")
        mm = np.isfinite(nddi) & np.isfinite(nd) & veg
        c = float(np.corrcoef(nddi[mm], nd[mm])[0, 1]) if mm.sum() > 100 else float("nan")
        check(t + " NDDI higher where the vegetation is drier (negative correlation with NDMI)", c < 0, "r = %.2f" % c)
        aot = ld(t, "vals_aot_off")
        check(t + " AOT within 0…0.6", np.nanmin(aot) >= 0 and np.nanmax(aot) <= 0.6, "min %.3f, max %.3f" % (np.nanmin(aot), np.nanmax(aot)))
        cl = ld(t, "vals_mstress_off")
        m, _ = q(cl, forest)
        check(t + " Moisture Stress: forest in the moist classes (NDMI > 0.2)", m > 0.2, "forest median NDMI(B08) %.3f" % m)
        for p in ("ndvidiff", "ndviz", "ndvidiff2"):
            v = ld(t, "vals_%s_off" % p)
            fin = np.isfinite(v)
            share = float((fin & forest).sum() / max(1, fin.sum()))
            check(t + " %s only on forest" % p, share > 0.9, "%.1f %% of %d product pixels inside the forest mask" % (100 * share, fin.sum()))
            rng = {"ndvidiff": 1, "ndvidiff2": 2, "ndviz": 20}[p]
            check(t + " %s in its range" % p, np.nanmax(np.abs(v)) <= rng, "max |v| %.3f (range ±%s)" % (np.nanmax(np.abs(v)), rng))
        v = ld(t, "vals_discoch_off")       # WSL product: probability in %, beech-dominated forest only
        fin = np.isfinite(v)
        check(t + " DiscoCH 0…100 %, on forest", fin.any() and np.nanmin(v) >= 0 and np.nanmax(v) <= 100 and float((fin & forest).sum()) / fin.sum() > 0.9,
              "min %.0f, max %.0f, %.1f %% of %d pixels inside the forest mask" % (np.nanmin(v), np.nanmax(v), 100 * float((fin & forest).sum()) / max(1, fin.sum()), fin.sum()))
        for p in ("vhidef", "vhiext"):
            v = ld(t, "vals_%s_off" % p)
            check(t + " %s ≥ 0, forest only" % p, np.nanmin(v) >= 0 and float((np.isfinite(v) & ~forest).sum()) / max(1, np.isfinite(v).sum()) < 0.1,
                  "min %.0f, max %.0f, %.1f %% outside the habitat forest mask" % (np.nanmin(v), np.nanmax(v), 100 * float((np.isfinite(v) & ~forest).sum()) / max(1, np.isfinite(v).sum())))
    # Aletsch (S10): snow, ice and terrain shadow
    t = "S10"
    scl = ld(t, "cls_scl_off")
    snow = scl == 11
    m, n = q(ld(t, "vals_ndsi_off"), snow)
    check(t + " NDSI snow / ice > 0.42", m > 0.42, "median %.3f over %d SCL snow pixels" % (m, n))
    tile = ld(t, "tile_ndsi_off")
    blue = (tile[..., 0] == 0) & (tile[..., 1] == 204) & (tile[..., 2] == 255)
    check(t + " NDSI snow drawn in blue", blue[snow].mean() > 0.8, "%.1f %% of the SCL snow pixels blue" % (100 * blue[snow].mean()))
    terr = ld(t, "vals_terrain_off")
    sh = ld(t, "tile_terrain_off")
    shade = (sh[..., 0] == 70) & (sh[..., 1] == 45) & (sh[..., 2] == 130)
    check(t + " terrain: incidence 0…180°, shadow (200) present in the Alps", np.nanmax(terr) <= 180 and shade.sum() > 0,
          "max angle %.0f°, %d shadow pixels" % (np.nanmax(terr), shade.sum()))
    # cloudy Aarau (B10): the two cloud products agree
    t = "B10"
    scl, cm = ld(t, "cls_scl_off"), ld(t, "cls_cloud_off")
    sc_cloud = np.isin(scl, [8, 9, 10])
    om_cloud = np.isin(cm, [1, 2])
    agree = float(((sc_cloud == om_cloud) & (scl > 0)).sum() / max(1, (scl > 0).sum()))
    check(t + " SCL clouds (8, 9, 10) and OmniCloudMask clouds (1, 2) agree", agree > 0.8, "%.1f %% agreement" % (100 * agree))
    json.dump(dict(stats=out, checks=checks), open(os.path.join(os.path.dirname(a.web.rstrip("/")), "semantics.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
