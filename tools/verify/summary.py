#!/usr/bin/env python3
"""Summary per layer of compare.json (regression, web vs rasterio) for the report.
  python3 tools/verify/summary.py DIR   (DIR holds compare.json)
"""
import json
import os
import sys
from collections import defaultdict


def main():
    d = sys.argv[1]
    c = json.load(open(os.path.join(d, "compare.json")))
    per = defaultdict(lambda: dict(n=0, reg_diff=[], tile_exact=0, tile_tol=[], tile_bad=[], vals_exact=0, vals_bad=[], errors=[],
                                   scenes_bad=[], map_vs_dl=[]))
    for key, r in c.items():
        tile, lk = key.split("/")
        lid = lk.rsplit("_", 1)[0]
        p = per[lid]
        p["n"] += 1
        for k, v in r.items():
            if k.startswith(("old_", "new-noworker_")) and v != "identical":
                p["reg_diff"].append("%s %s: %s" % (key, k, v))
        if r.get("errors"):
            p["errors"].append("%s: %s" % (key, r["errors"]))
        if r.get("ref_error"):
            p["errors"].append("%s ref: %s" % (key, r["ref_error"]))
        t = r.get("ref_tile")
        if isinstance(t, dict):
            if t["alpha"] == 0 and t["max"] == 0:
                p["tile_exact"] += 1
            elif t["alpha"] == 0:
                p["tile_tol"].append("%s max %d, >1 on %d px" % (key, t["max"], t["n_gt1"]))
            else:
                p["tile_bad"].append("%s %s" % (key, t))
        elif t is not None:
            p["errors"].append("%s tile: %s" % (key, t))
        for vk in ("ref_vals", "ref_cls"):
            v = r.get(vk)
            if isinstance(v, dict):
                if v["nan_mismatch"] == 0 and v["n_gt"] == 0:
                    p["vals_exact"] += 1
                else:
                    p["vals_bad"].append("%s %s" % (key, v))
            elif isinstance(v, str):
                p["vals_bad"].append("%s %s" % (key, v))
        for sk in ("ref_scenes_ok", "ref_refscenes_ok"):
            if r.get(sk) is False:
                p["scenes_bad"].append(key + " " + sk)
        if isinstance(r.get("map_vs_download"), dict) and r["map_vs_download"]["nan_mismatch"]:
            p["map_vs_dl"].append("%s: %d px" % (key, r["map_vs_download"]["nan_mismatch"]))
    print("| layer | entries | regression old / no-worker | map tile vs rasterio | values vs rasterio | notes |")
    print("| --- | --- | --- | --- | --- | --- |")
    for lid in sorted(per):
        p = per[lid]
        reg = "identical" if not p["reg_diff"] else "%d differ" % len(p["reg_diff"])
        tile = "%d exact" % p["tile_exact"] + (", %d within JPEG tolerance" % len(p["tile_tol"]) if p["tile_tol"] else "") + \
            (", **%d differ**" % len(p["tile_bad"]) if p["tile_bad"] else "")
        vals = ("%d exact" % p["vals_exact"] if p["vals_exact"] else "–") + (", **%d differ**" % len(p["vals_bad"]) if p["vals_bad"] else "")
        notes = "; ".join(p["errors"][:2] + p["scenes_bad"][:2] + (["map shows more than download: " + ", ".join(p["map_vs_dl"])] if p["map_vs_dl"] else []))
        print("| %s | %d | %s | %s | %s | %s |" % (lid, p["n"], reg, tile, vals, notes[:300]))
    print()
    for lid in sorted(per):
        p = per[lid]
        for x in p["reg_diff"] + p["tile_bad"] + p["vals_bad"] + p["tile_tol"][:3]:
            print("-", x[:400])


if __name__ == "__main__":
    main()
