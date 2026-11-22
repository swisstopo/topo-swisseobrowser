#!/usr/bin/env python3
"""Independent reference of the swissEO Browser layers with rasterio / GDAL and numpy.

The COGs are read with GDAL (not geotiff.js) and every formula, mask and colour is computed here with numpy from
the documented rules; only the colour ramps / palettes are taken from the page (meta.json of drive.py), so that the
ramps themselves are compared verbatim. Sampling follows the page's documented rule: the coarsest overview whose
pixel is at most 1.35 × the target pixel, nearest source pixel at each output pixel centre.

Used by tools/verify/compare.py; run as a script it prints a self test.
"""
import functools
import json
import math
import os
import urllib.request

import numpy as np
import rasterio
from rasterio.windows import Window

GDAL_ENV = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
                VSI_CACHE=True, VSI_CACHE_SIZE=512 * 1024 * 1024, GDAL_HTTP_MULTIRANGE="YES",
                GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES", GDAL_CACHEMAX=1024, GDAL_HTTP_MAX_RETRY=4,
                GDAL_HTTP_RETRY_DELAY=1)
ENV = rasterio.Env(**GDAL_ENV)
ENV.__enter__()

STAC = "https://data.geo.admin.ch/api/stac/v0.9"
COLL = "ch.swisstopo.swisseo_s2-sr_v200"
DATA = "https://data.geo.admin.ch/" + COLL + "/"
SUFFIX = dict(b01="b01_60m", b02="b02_10m", b03="b03_10m", b04="b04_10m", b05="b05_20m", b06="b06_20m", b07="b07_20m",
              b08="b08_10m", b8a="b8a_20m", b09="b09_60m", b11="b11_20m", b12="b12_20m", aot="aot_60m",
              scl="scl_20m", cloud="cloudmask_10m", terrain="terrainmask_10m", tci="tci_10m")
MASK_BASE = "https://s3-topo-satromo-prod.s3.eu-central-1.amazonaws.com/data/MASKS/Vegetation/"
HABITAT = [("0000-00-00", "habitatv1-0_2022_CLCplus_2021"), ("2024-07-12", "habitatv1-1_2024_CLCplus_2023"),
           ("2025-12-11", "habitatv1-2_2025_CLCplus_2023")]


def asset_url(item, band):
    return DATA + item + "/swisseo_s2-sr_v200_mosaic_" + item + "_" + SUFFIX[band] + ".tif"


def veg_url(kind, date):
    f = [h[1] for h in HABITAT if h[0] <= date][-1]
    return MASK_BASE + kind + "_mask_2056_" + f + ".tif"


# ---------------------------------------------------------------- reading
@functools.lru_cache(maxsize=None)
def pyramid(url):
    """Levels of a COG as the page lists them: full image and overviews, sorted by pixel size."""
    with rasterio.open("/vsicurl/" + url) as ds:
        t = ds.transform
        ox, oy, W0, H0 = t.c, t.f, ds.width, ds.height
        extW, extH = W0 * abs(t.a), H0 * abs(t.e)
        n_ov = len(ds.overviews(1))
    levels = [dict(ovl=None, w=W0, h=H0)]
    for i in range(n_ov):
        with rasterio.open("/vsicurl/" + url, overview_level=i) as o:
            levels.append(dict(ovl=i, w=o.width, h=o.height))
    for l in levels:
        l["rx"], l["ry"] = extW / l["w"], extH / l["h"]
    levels.sort(key=lambda l: l["rx"])
    return dict(ox=ox, oy=oy, levels=levels)


_open = {}


def dataset(url, ovl):
    k = (url, ovl)
    if k not in _open:
        _open[k] = rasterio.open("/vsicurl/" + url, overview_level=ovl) if ovl is not None else rasterio.open("/vsicurl/" + url)
    return _open[k]


def read_grid(url, bbox, W, H, fill=0, nb=1, with_valid=False):
    """W x H grid of the first nb bands, aligned to bbox. None when the box misses the image."""
    p = pyramid(url)
    target, targetY = (bbox[2] - bbox[0]) / W, (bbox[3] - bbox[1]) / H
    li = 0
    for i, l in enumerate(p["levels"]):
        if l["rx"] <= target * 1.35:
            li = i
        else:
            break
    lv = p["levels"][li]
    x0 = max(0, math.floor((bbox[0] - p["ox"]) / lv["rx"]))
    x1 = min(lv["w"], math.ceil((bbox[2] - p["ox"]) / lv["rx"]))
    y0 = max(0, math.floor((p["oy"] - bbox[3]) / lv["ry"]))
    y1 = min(lv["h"], math.ceil((p["oy"] - bbox[1]) / lv["ry"]))
    if x1 <= x0 or y1 <= y0:
        return None
    ds = dataset(url, lv["ovl"])
    win = Window(x0, y0, x1 - x0, y1 - y0)
    arr = ds.read(list(range(1, nb + 1)), window=win).astype(np.float32)
    i = np.arange(W, dtype=np.float64)
    j = np.arange(H, dtype=np.float64)
    sc = np.floor((bbox[0] + (i + 0.5) * target - p["ox"]) / lv["rx"]).astype(np.int64)
    sr = np.floor((p["oy"] - (bbox[3] - (j + 0.5) * targetY)) / lv["ry"]).astype(np.int64)
    okc, okr = (sc >= x0) & (sc < x1), (sr >= y0) & (sr < y1)
    out = np.full((nb, H, W), fill, np.float32)
    rr, cc = np.ix_(np.where(okr)[0], np.where(okc)[0])
    out[:, rr, cc] = arr[:, (sr[okr] - y0)[:, None], (sc[okc] - x0)[None, :]]
    valid = None
    flags = ds.mask_flag_enums[0]
    if any(f.name == "per_dataset" for f in flags):
        m = ds.read_masks(1, window=win)
        valid = np.zeros((H, W), np.uint8)
        valid[rr, cc] = m[(sr[okr] - y0)[:, None], (sc[okc] - x0)[None, :]] > 0
        out[:, valid == 0] = 0
    if with_valid:
        return out, valid
    return out


# ---------------------------------------------------------------- catalogue
def get_json(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


ITEM_RE = __import__("re").compile(r"^\d{4}-\d{2}-\d{2}t\d{6}$")


@functools.lru_cache(maxsize=None)
def stac_day(coll, date):
    url = STAC + "/collections/" + coll + "/items?limit=100&datetime=%sT00:00:00Z/%sT23:59:59Z" % (date, date)
    out = []
    while url:
        j = get_json(url)
        out += [f for f in j["features"] if ITEM_RE.match(f["id"])]       # as stacAll: dated item ids only
        url = next((l["href"] for l in j.get("links", []) if l.get("rel") == "next"), None)
    return out


def s2_scenes(date, cc=100):
    """Every S2-SR mosaic of the day with cloud cover <= cc (unknown passes), most recent first."""
    ids = []
    for f in stac_day(COLL, date):
        if not f["id"].startswith(date):
            continue
        c = cloud_of(f["id"])
        if c is None or c <= cc:
            ids.append(f["id"])
    return sorted(ids, reverse=True)


@functools.lru_cache(maxsize=None)
def cloud_of(item):
    try:
        v = get_json(DATA + item + "/swisseo_s2-sr_v200_mosaic_" + item + "_metadata.json")["PROPERTIES"].get("CLOUDPERCENTAGE")
        return float(v) if v is not None and math.isfinite(float(v)) else None    # a string in metadata.json
    except Exception:
        return None


# ---------------------------------------------------------------- formulas
def phys(b, dn):
    return dn * 0.001 if b == "aot" else dn * 0.0001 + -0.1


def phys_idx(b, dn):
    p = phys(b, dn)
    return np.where(p > 0, p, 0.0)


def nd(v, s=None):
    return (v[0] - v[1]) / (v[0] + v[1])


def nddi(v, s=None):
    ndvi = (v[0] - v[1]) / (v[0] + v[1])
    ndwi = (v[2] - v[0]) / (v[2] + v[0]) if s and s.get("ndwi") == "green" else (v[0] - v[3]) / (v[0] + v[3])
    return np.clip((ndvi - ndwi) / (ndvi + ndwi), -1, 1)


FN = {
    "ndvi": nd, "ndwi": nd, "ndmi": nd, "ndsi": nd, "nbr": nd, "ndre": nd, "mstress": nd, "analyst": nd,
    "ndvidiff22": nd, "ndvidiff23": nd, "nddi": nddi, "nddichg": nddi,
    "evi": lambda v, s=None: 2.5 * (v[0] - v[1]) / (v[0] + 6 * v[1] - 7.5 * v[2] + 1),
    "savi": lambda v, s=None: (v[0] - v[1]) / (v[0] + v[1] + 0.428) * 1.428,
    "mtvi2": lambda v, s=None: 1.5 * (1.2 * (v[0] - v[2]) - 2.5 * (v[1] - v[2])) /
        np.sqrt((2 * v[0] + 1) ** 2 - (6 * v[0] - 5 * np.sqrt(v[1])) - 0.5),
    # Barren Soil: the statistic is the BSI as the page summarises it (statFn, without the 2.5 of the picture)
    "barren": lambda v, s=None: ((v[0] + v[1]) - (v[2] + v[3])) / ((v[0] + v[1]) + (v[2] + v[3])),
}

COG = {  # COG products: url pattern, scale, fill, missing, validity
    "ndvidiff": dict(scale=0.001, fill=32701, missing=32700, valid=lambda v, res: (v < 32700) & (ovr_free(res) | ((v >= -1000) & (v <= 1000)))),
    "ndviz": dict(scale=0.01, fill=32701, missing=32700, valid=lambda v, res: (v < 32700) & (ovr_free(res) | ((v >= -2000) & (v <= 2000)))),
    "ndvidiff2": dict(scale=0.001, fill=32701, missing=None, valid=lambda v, res: (v >= -2000) & (v <= 2000)),
}


def ovr_free(res):
    return res is None or res * 1.35 < 20


def cog_url(lid, item):
    if lid == "ndvidiff2":
        return "https://cms.geo.admin.ch/Topo/umweltbeobachtung/beispiele/NDVIDIFFV2/swisseo_s2-sr_v200_mosaic_" + item + "_ndvidiff-forest_10m.tif"
    prod = {"ndvidiff": "ndvi_diff", "ndviz": "ndvi_z"}[lid]
    coll = "ch.swisstopo.swisseo_" + prod + "_v100"
    for f in stac_day(coll, item[:10]):
        if f["id"] == item:
            for k, a in f["assets"].items():
                if k.endswith("_forest-10m.tif") and "/" + coll + "/" in a["href"]:
                    return a["href"]
    return "https://data.geo.admin.ch/" + coll + "/" + item + "/swisseo_" + prod + "_v100_mosaic_" + item + "_forest-10m.tif"


def vhi_url(item, kind="forest"):
    coll = "ch.swisstopo.swisseo_vhi_v100"
    for f in stac_day(coll, item[:10]):
        if f["id"] == item:
            for k, a in f["assets"].items():
                if k.endswith("_" + kind + "-10m.tif") and "/" + coll + "/" in a["href"]:
                    return a["href"]
    return "https://data.geo.admin.ch/" + coll + "/" + item + "/" + coll + "_mosaic_" + item + "_" + kind + "-10m.tif"


# ---------------------------------------------------------------- colours (Uint8ClampedArray: round half to even)
def u8(x):
    return np.rint(np.clip(np.nan_to_num(x, nan=0.0), 0, 255)).astype(np.uint8)


def ramp_rgb(stops, v):
    """The page's ramp: linear between stops, ends clamped. Returns H x W x 3 float and a finite mask."""
    xs = np.array([s[0] for s in stops], np.float64)
    cs = np.array([s[1] for s in stops], np.float64)
    fin = np.isfinite(v)
    vv = np.where(fin, v, xs[0])
    out = np.empty(v.shape + (3,), np.float64)
    lo = vv <= xs[0]
    hi = vv > xs[-1]
    # index of the first stop >= v (as the page's search), for xs[0] < v <= xs[-1]
    idx = np.clip(np.searchsorted(xs, vv, side="left"), 1, len(xs) - 1)
    a, b = xs[idx - 1], xs[idx]
    den = b - a
    den = np.where(den == 0, 1, den)
    t = (vv - a) / den
    for c in range(3):
        out[..., c] = cs[idx - 1, c] + (cs[idx, c] - cs[idx - 1, c]) * t
    out[lo] = cs[0]
    out[hi] = cs[-1]
    return out, fin


def ramp_from_meta(meta, lid):
    l = meta["L"][lid]
    return l["rampStops"], l["domain"]


# ---------------------------------------------------------------- settings
def settings(meta, lid, masks):
    s = dict(meta["defs"][lid])
    if masks == "off":
        s.update(cloud=False, shadow=False, terrain=False, illum=False, veg="off")
    return s


def veg_on(v):
    return v not in (None, "", "off")


def veg_kind(v):
    return v if v in ("forest", "vegetation") else None


def veg_mask(v, date, bbox, W, H):
    k = veg_kind(v)
    if k is None:
        raise ValueError("vegetation mask %r not supported by the reference" % v)
    a = read_grid(veg_url(k, date), bbox, W, H, 0)
    m = np.zeros((H, W), np.uint8)
    if a is not None:
        m[a[0] != 0] = 1
    return m


def terr_out(s):
    if not (s.get("terrain") or s.get("illum")):
        return None
    thr = s.get("illumThr", 70)
    return lambda v: (bool(s.get("terrain")) & (v == 200)) | (bool(s.get("illum")) & (v >= thr) & (v <= 180))


MASKABLE = {"rgb", "index", "cont", "terrain", "fnrgb", "diff2", "fnclass", "wincomp"}


# ---------------------------------------------------------------- one scene (renderScene)
def render_scene(meta, lid, s, sid, bbox, W, H, edge=False):
    L = meta["L"][lid]
    t = L["type"]
    bands = L.get("bands") or [L.get("band")]
    s2 = L["source"] == "s2"
    maskable = t in MASKABLE and s2
    cog = lid in COG
    tci = L.get("tci")
    allb = [] if tci else bands + [b for b in (L.get("bg") or []) if b not in bands]
    if cog:
        a = [read_grid(cog_url(lid, sid), bbox, W, H, COG[lid]["fill"])]
    elif tci:
        r = read_grid(asset_url(sid, "tci"), bbox, W, H, 0, nb=3, with_valid=True)
        a = None if r is None else list(r[0])
        valid = None if r is None else r[1]
    else:
        a = [read_grid(asset_url(sid, b), bbox, W, H, 255 if b == "terrain" else 0) for b in allb]
    if a is None or any(x is None for x in a):
        return None
    a = [x[0] if x.ndim == 3 else x for x in a]
    cm = read_grid(asset_url(sid, "cloud"), bbox, W, H, 0)[0] if maskable and (s["cloud"] or s["shadow"]) else None
    tout = terr_out(s) if maskable else None
    tm = read_grid(asset_url(sid, "terrain"), bbox, W, H, 255)[0] if tout else None
    vm = veg_mask(s["veg"], sid[:10], bbox, W, H) if s2 and veg_on(s["veg"]) else None
    mk = np.zeros((H, W), bool)
    if vm is not None:
        mk |= vm == 0
    if cm is not None:
        mk |= (bool(s["cloud"]) & ((cm == 1) | (cm == 2))) | (bool(s["shadow"]) & (cm == 3))
    if tm is not None:
        mk |= tout(tm)
    img = np.zeros((H, W, 4), np.uint8)
    held = None

    def put(sel, rgb):
        img[sel, :3] = u8(rgb[sel] if rgb.ndim == 3 else rgb)
        img[sel, 3] = 255

    nb = len(bands)
    # readVals: every band of the layer must have data; reflectance below 0 is set to 0
    if not tci and not cog and t not in ("class", "terrain"):
        ok = np.ones((H, W), bool)
        vals = []
        for i in range(nb):
            ok &= a[i] != 0
            vals.append(phys_idx(bands[i], a[i].astype(np.float64)))
    gain, gamma = s["gain"], s["gamma"]
    rg = [s["r"], s["g"], s["b"]]

    def rng(v, r):
        return 255 * np.clip((v - r[0]) / ((r[1] - r[0]) or 1e-6), 0, 1)

    if tci:
        val = valid if valid is not None else ~((a[0] == 0) & (a[1] == 0) & (a[2] == 0))
        sel = (val > 0) & ~mk
        out = np.zeros((H, W, 3))
        for c in range(3):
            v = np.clip(a[c] / 255 * gain, 0, 1)
            if gamma != 1:
                v = v ** (1 / gamma)
            out[..., c] = rng(v, rg[c])
        drop = dark_edges(a, valid, sid, bbox, W, H) if edge else None
        if drop is not None:
            held = np.zeros((H, W, 4), np.uint8)
            hs = sel & drop
            held[hs, :3] = u8(out[hs])
            held[hs, 3] = 255
            sel = sel & ~drop
        put(sel, out)
        return img, held
    if t == "rgb" and L.get("look") == "hon":
        sel = ~((a[0] == 0) & (a[1] == 0) & (a[2] == 0)) & ~mk
        out = np.zeros((H, W, 3))
        for c in range(3):
            x = phys(bands[c], a[c].astype(np.float64)) * gain
            v = np.clip(np.where(x > 0.15, np.cbrt(0.6 * x), 2.9876031644 * x), 0, 1)
            if gamma != 1:
                v = v ** (1 / gamma)
            out[..., c] = rng(v, rg[c])
        put(sel, out)
        return img, None
    if t == "fnrgb":  # Barren Soil
        v0, v1, v2, v3 = vals
        bsi = 2.5 * ((v0 + v1) - (v2 + v3)) / ((v0 + v1) + (v2 + v3))
        out = np.stack([2.5 * bsi, v2, v0], -1)
        out[v2 > 0.6] = 1
        sel = ok & ~mk
        put(sel, 255 * np.clip(out, 0, 1))
        return img, None
    if t == "fnclass":
        return None, "fdc"  # compared separately (QuickJS run of the original script)
    if L.get("steps") or L.get("classify"):
        v = FN[lid](vals, s)
        sel = ok & ~mk & np.isfinite(v)
        out = np.zeros((H, W, 3))
        if L.get("steps"):
            st = L["steps"]
            out[:] = st["other"]
            done = np.zeros((H, W), bool)
            for thr, col in st["steps"]:
                m = ~done & (v < thr)
                out[m] = col
                done |= m
        else:
            cl = L["classify"]
            out[:] = cl[-1][1]
            done = np.zeros((H, W), bool)
            for thr, col, _ in cl:
                thr = np.inf if thr is None else thr
                m = ~done & (v <= thr)
                out[m] = col
                done |= m
        put(sel, out)
        return img, None
    if t == "rgb":
        g = meta["consts"]["BASE_GAIN"] * (L.get("gainMul") or 1) * gain
        ig = 1 / (meta["consts"]["BASE_GAMMA"] * gamma)
        sel = ~((a[0] == 0) & (a[1] == 0) & (a[2] == 0)) & ~mk
        out = np.zeros((H, W, 3))
        for c in range(3):
            v = np.clip(phys(bands[c], a[c].astype(np.float64)) * g, 0, 1) ** ig
            out[..., c] = rng(v, rg[c])
        put(sel, out)
        return img, None
    if L.get("threshold") is not None:  # NDSI
        thr = s.get("thr") if s.get("thr") is not None else L["threshold"]
        sel = (a[0] != 0) & (a[1] != 0) & ~mk & ok
        v = nd(vals)
        snow = sel & (v > thr)
        bi = [allb.index(b) for b in L["bg"]]
        out = np.stack([255 * np.clip(2.5 * phys("b04", a[i].astype(np.float64)), 0, 1) for i in bi], -1)
        put(sel & ~snow, out)
        put(snow, np.array([0, 204, 255], np.float64) * np.ones((H, W, 1)))
        return img, None
    if L.get("rampStops"):
        stops, (d0, d1) = L["rampStops"], L["domain"]
        k2 = (d1 - d0) / ((s["max"] - s["min"]) or 1e-9)
        col = lambda v: ramp_rgb(stops, d0 + (v - s["min"]) * k2)
        if t == "index":
            v = FN[lid](vals, s)
            rgb, fin = col(v)
            put(ok & ~mk & fin, rgb)
            return img, None
        x = a[0].astype(np.float64)
        if cog:
            c = COG[lid]
            res = (bbox[2] - bbox[0]) / W
            rgb, fin = col(x * c["scale"])
            good = ~mk & (x != c["fill"]) & c["valid"](x, res)
            put(good & fin, rgb)
            if c["missing"] is not None:
                put(~mk & (x == c["missing"]), np.array(meta["consts"]["MISSING_RGB"], np.float64) * np.ones((H, W, 1)))
            return img, None
        if t == "cont":
            rgb, fin = col(phys(L["band"], x))
            put(~mk & (x != 0) & fin, rgb)
            return img, None
        # terrain
        rgb, fin = col(x)
        lit = ~mk & (x <= 180)
        put(lit & fin, rgb)
        put(~mk & (x == 200), np.array(meta["consts"]["SHADOW_RGB"], np.float64) * np.ones((H, W, 1)))
        return img, None
    if t == "class":
        pal = meta["ramps"]["P_SCL" if lid == "scl" else "P_CLOUD"]
        x = a[0].astype(np.int64)
        sel0 = np.ones((H, W), bool) if vm is None else vm != 0
        for key, e in (pal.items() if isinstance(pal, dict) else enumerate(pal)):
            if e and e[1]:
                put(sel0 & (x == int(key)), np.array(e[1], np.float64) * np.ones((H, W, 1)))
        return img, None
    return None, "unsupported"


@functools.lru_cache(maxsize=None)
def edge_zone(sid):
    """Edge zone of a scene: chessboard distance to the TCI footprint's edge (internal mask at about 160 m) <= 2 km."""
    from scipy.ndimage import distance_transform_cdt
    url = asset_url(sid, "tci")
    p = pyramid(url)
    cand = [l for l in p["levels"] if l["rx"] <= 170]
    lv = cand[-1] if cand else p["levels"][0]
    ds = dataset(url, lv["ovl"])
    m = ds.read_masks(1) > 0
    pad = np.pad(m, 1, constant_values=False)                 # outside the image = no data
    d = distance_transform_cdt(pad, metric="chessboard")[1:-1, 1:-1]
    return dict(zone=d <= 2000 / lv["rx"], rx=lv["rx"], ry=lv["ry"], ox=p["ox"], oy=p["oy"], W=lv["w"], H=lv["h"])


def dark_edges(a, valid, sid, bbox, W, H):
    ez = edge_zone(sid)
    rx, ry = (bbox[2] - bbox[0]) / W, (bbox[3] - bbox[1]) / H
    zc = np.floor((bbox[0] + (np.arange(W) + 0.5) * rx - ez["ox"]) / ez["rx"]).astype(int)
    zr = np.floor((ez["oy"] - (bbox[3] - (np.arange(H) + 0.5) * ry)) / ez["ry"]).astype(int)
    inside = (zr[:, None] >= 0) & (zc[None, :] >= 0) & (zr[:, None] < ez["H"]) & (zc[None, :] < ez["W"])
    z = np.ones((H, W), bool)
    rr, cc = np.clip(zr, 0, ez["H"] - 1), np.clip(zc, 0, ez["W"] - 1)
    zin = ez["zone"][rr[:, None], cc[None, :]]
    z = ~inside | zin                                          # outside the zone grid counts as edge zone
    val = np.ones((H, W), bool) if valid is None else valid > 0
    drop = z & val & ((a[0] + a[1] + a[2]) / 3 < meta_edge_dark)
    if not drop.any():
        return None
    g = max(1, round(10 / rx))
    from scipy.ndimage import maximum_filter
    h = maximum_filter(drop.astype(np.uint8), size=(1, 2 * g + 1), mode="constant")
    v = maximum_filter(h, size=(2 * g + 1, 1), mode="constant")
    return drop | (z & (v > 0))


meta_edge_dark = 40


# ---------------------------------------------------------------- the tile of a day (renderTile)
def render_tile(meta, lid, s, scenes, bbox, W, H):
    L = meta["L"][lid]
    out, helds = None, []
    edge = bool(L.get("tci")) and len(scenes) > 1
    for sid in scenes:
        r = render_scene(meta, lid, s, sid, bbox, W, H, edge)
        if r is None:
            continue
        im, held = r
        if im is None:
            return None, held
        if held is not None:
            helds.append(held)
        if out is None:
            out = im
        else:
            f = (out[..., 3] == 0) & (im[..., 3] != 0)
            out[f] = im[f]
        if (out[..., 3] != 0).all():
            break
    if out is not None:
        for h in helds:
            f = (out[..., 3] == 0) & (h[..., 3] != 0)
            out[f] = h[f]
    return out, None


# ---------------------------------------------------------------- values (sampleAoi, as the TIFF-32 download)
def sample(meta, lid, s, scenes, bbox, W, H, stat_fn=None):
    L = meta["L"][lid]
    t = L["type"]
    t = "index" if t in ("fnrgb", "diff2", "wincomp") else t
    bands = L.get("bands") or [L.get("band")]
    vals = np.full((H, W), np.nan)
    cls = np.full((H, W), -1, np.int16) if t in ("class", "fnclass") else None
    done = np.zeros((H, W), bool)
    if veg_on(s["veg"]) and L["source"] == "s2" and scenes:
        vm = veg_mask(s["veg"], scenes[0][:10], bbox, W, H)
        done |= vm == 0
    res = (bbox[2] - bbox[0]) / W
    for sid in scenes:
        if done.all():
            break
        if lid in COG:
            c = COG[lid]
            a = read_grid(cog_url(lid, sid), bbox, W, H, c["fill"])
            if a is None:
                continue
            x = a[0].astype(np.float64)
            g = ~done & (x != c["fill"]) & c["valid"](x, res)
            vals[g] = x[g] * c["scale"]
            done |= g
            continue
        cov_band = "b04" if L.get("band") == "cloud" else bands[0]
        first = read_grid(asset_url(sid, cov_band), bbox, W, H, 255 if cov_band == "terrain" else 0)
        if first is None:
            continue
        first = first[0]
        has = ~done & ((first != 255) if t == "terrain" else (first != 0))
        if not has.any():
            continue
        use_mask = t != "class"
        tout = None if not use_mask else (terr_out(dict(terrain=False, illum=s.get("illum"), illumThr=s.get("illumThr")))
                                          if t == "terrain" else terr_out(s))
        mclouds = use_mask and (s["cloud"] or s["shadow"])
        if mclouds:
            cm = read_grid(asset_url(sid, "cloud"), bbox, W, H, 0)[0]
            m = (bool(s["cloud"]) & ((cm == 1) | (cm == 2))) | (bool(s["shadow"]) & (cm == 3))
        else:
            m = np.zeros((H, W), bool)
        if tout:
            tm = read_grid(asset_url(sid, "terrain"), bbox, W, H, 255)[0]
            m |= tout(tm)
        m &= has
        done |= m
        has &= ~m
        if not has.any():
            continue
        need = bands[1:] if cov_band == bands[0] else bands
        rest = [read_grid(asset_url(sid, b), bbox, W, H, 255 if b == "terrain" else 0) for b in need]
        if any(x is None for x in rest):
            continue
        a = ([first] if cov_band == bands[0] else []) + [x[0] for x in rest]
        if t == "fnclass":
            return None  # separate check
        if t == "class":
            v = a[0]
            g = has & ~((L["band"] == "scl") & (v == 0))
            cls[g] = v[g]
            done |= g
            continue
        if t == "terrain":
            v = a[0]
            skip = (v > 180) & (v != 200)
            g = has & ~skip
            lit = g & (v != 200)
            vals[lit] = v[lit]
            done |= g
            continue
        if t == "index":
            allok = np.ones((H, W), bool)
            for x in a:
                allok &= x != 0
            fn = stat_fn or FN[lid]
            v = fn([phys_idx(bands[i], a[i].astype(np.float64)) for i in range(len(bands))], s)
            g = has & allok
            vals[g] = v[g]
        elif t == "cont":
            vals[has] = phys(L["band"], a[0].astype(np.float64))[has]
        done |= has
    return cls if cls is not None else vals.astype(np.float32)


# ---------------------------------------------------------------- special layers
def add_days(d, n):
    import datetime as dt
    return (dt.date.fromisoformat(d) + dt.timedelta(days=n)).isoformat()


def year_back(d):
    return "%04d%s" % (int(d[:4]) - 1, d[4:])


def s2_items(frm, to):
    """S2-SR item ids from frm to to (dates), via STAC per day."""
    out, d = [], frm
    while d <= to:
        out += [f["id"] for f in stac_day(COLL, d) if f["id"].startswith(d)]
        d = add_days(d, 1)
    return out


def ref_selection(date, ref_date=None):
    """Reference of the two-date layers: days within ±20 days of the target, clearest first (cloud cover of the
    clearest scene of the day), then nearest; at most 6 days; scenes of a day most recent first."""
    target = ref_date or year_back(date)
    ids = s2_items(add_days(target, -20), add_days(target, 20))
    by = {}
    for i in ids:
        d = i[:10]
        c = cloud_of(i)
        e = by.setdefault(d, dict(ids=[], cloud=101))
        e["ids"].append(i)
        if c is not None:
            e["cloud"] = min(e["cloud"], c)
    import datetime as dt
    t = dt.date.fromisoformat(target)
    days = sorted(by.items(), key=lambda kv: (((-(kv[0] == target)) if ref_date else 0), kv[1]["cloud"],
                                              abs((dt.date.fromisoformat(kv[0]) - t).days)))[:6]
    return dict(target=target, dates=[d for d, _ in days], scenes=[i for _, e in days for i in sorted(e["ids"], reverse=True)])


def date_index(lid, s, scenes, bbox, W, H):
    """Index of one date for the map of the two-date layers: per pixel the first scene with data that is not masked."""
    bands = {"nddichg": ["b08", "b04", "b03", "b11"], "analyst": ["b08", "b04"]}[lid]
    out = np.full((H, W), np.nan)
    done = np.zeros((H, W), bool)
    tout = terr_out(s)
    for sid in scenes:
        a = [read_grid(asset_url(sid, b), bbox, W, H, 0) for b in bands]
        if any(x is None for x in a):
            continue
        a = [x[0] for x in a]
        ok = ~done
        for x in a:
            ok &= x != 0
        if s["cloud"] or s["shadow"]:
            cm = read_grid(asset_url(sid, "cloud"), bbox, W, H, 0)[0]
            ok &= ~((bool(s["cloud"]) & ((cm == 1) | (cm == 2))) | (bool(s["shadow"]) & (cm == 3)))
        if tout:
            tm = read_grid(asset_url(sid, "terrain"), bbox, W, H, 255)[0]
            ok &= ~tout(tm)
        v = FN[lid]([phys_idx(bands[i], a[i].astype(np.float64)) for i in range(len(bands))], s)
        ok &= np.isfinite(v)
        out[ok] = v[ok]
        done |= ok
    return out.astype(np.float32)


def diff2_tile(meta, lid, s, date, scenes, ref_scenes, bbox, W, H):
    A = date_index(lid, s, scenes, bbox, W, H)
    B = date_index(lid, s, ref_scenes, bbox, W, H)
    dif = (A.astype(np.float64) - B.astype(np.float64)).astype(np.float32)
    if veg_on(s["veg"]):
        vm = veg_mask(s["veg"], date, bbox, W, H)
        dif[vm == 0] = np.nan
    L = meta["L"][lid]
    stops, (d0, d1) = L["rampStops"], L["domain"]
    k2 = (d1 - d0) / ((s["max"] - s["min"]) or 1e-9)
    rgb, fin = ramp_rgb(stops, d0 + (dif.astype(np.float64) - s["min"]) * k2)
    img = np.zeros((H, W, 4), np.uint8)
    sel = fin & np.isfinite(dif)
    img[sel, :3] = u8(rgb[sel])
    img[sel, 3] = 255
    return img, dif


def window_index(lid, s, ids, bbox, W, H):
    med = lid == "ndvidiff23"
    tout = terr_out(s)
    best = np.full((H, W), -np.inf, np.float32)
    stack, cnt = [], np.zeros((H, W), np.int32)
    for sid in ids:
        a = [read_grid(asset_url(sid, b), bbox, W, H, 0) for b in ("b08", "b04")]
        if any(x is None for x in a):
            continue
        a = [x[0] for x in a]
        ok = (a[0] != 0) & (a[1] != 0)
        if s["cloud"] or s["shadow"]:
            cm = read_grid(asset_url(sid, "cloud"), bbox, W, H, 0)[0]
            ok &= ~((bool(s["cloud"]) & ((cm == 1) | (cm == 2))) | (bool(s["shadow"]) & (cm == 3)))
        if tout:
            tm = read_grid(asset_url(sid, "terrain"), bbox, W, H, 255)[0]
            ok &= ~tout(tm)
        x = nd([phys_idx("b08", a[0].astype(np.float64)), phys_idx("b04", a[1].astype(np.float64))])
        ok &= np.isfinite(x)
        cnt += ok
        if med:
            v = np.full((H, W), -32768, np.int32)
            v[ok] = np.floor(x[ok] * 10000 + 0.5)              # Math.round
            if ok.any():
                stack.append(v)
        else:
            best = np.where(ok & (x.astype(np.float32) > best), x.astype(np.float32), best)
    out = np.full((H, W), np.nan, np.float32)
    if not med:
        out[cnt > 0] = best[cnt > 0]
    elif stack:
        st = np.stack(stack).astype(np.float64)
        st[st == -32768] = np.nan
        srt = np.sort(st, 0)                                  # NaN last
        m = np.sum(~np.isnan(st), 0)
        idx = np.arange(H * W)
        flat = srt.reshape(len(stack), -1)
        mm = m.ravel()
        odd = flat[(np.maximum(mm, 1) - 1) // 2, idx]
        even = (flat[np.maximum(mm // 2 - 1, 0), idx] + flat[mm // 2 % len(stack), idx]) / 2
        v = np.where(mm % 2 == 1, odd, even) / 10000
        out = np.where(mm > 0, v, np.nan).reshape(H, W).astype(np.float32)
    return out


def window_ids(date, days):
    return sorted(s2_items(add_days(date, 1 - days), date), reverse=True)


def wincomp(meta, lid, s, date, scenes, bbox, W, H):
    days = s.get("days", 30)
    A = window_index(lid, s, scenes, bbox, W, H)
    ref_ids = window_ids(year_back(date), days)
    B = window_index(lid, s, ref_ids, bbox, W, H)
    dif = (A.astype(np.float64) - B.astype(np.float64)).astype(np.float32)
    if veg_on(s["veg"]):
        dif[veg_mask(s["veg"], date, bbox, W, H) == 0] = np.nan
        dif[veg_mask(s["veg"], year_back(date), bbox, W, H) == 0] = np.nan
    L = meta["L"][lid]
    stops, (d0, d1) = L["rampStops"], L["domain"]
    k2 = (d1 - d0) / ((s["max"] - s["min"]) or 1e-9)
    rgb, fin = ramp_rgb(stops, d0 + (dif.astype(np.float64) - s["min"]) * k2)
    img = np.zeros((H, W, 4), np.uint8)
    sel = fin & np.isfinite(dif)
    img[sel, :3] = u8(rgb[sel])
    img[sel, 3] = 255
    return img, dif, ref_ids


def vhi_items(frm, to):
    out, d = [], frm
    while d <= to:
        out += [f["id"] for f in stac_day("ch.swisstopo.swisseo_vhi_v100", d)]
        d = add_days(d, 1)
    return sorted(set(out))


def vhi_newest():
    import datetime as dt
    d = dt.date.today().isoformat()
    for _ in range(120):
        fs = stac_day("ch.swisstopo.swisseo_vhi_v100", d)
        if fs:
            return sorted(f["id"] for f in fs)[-1]
        d = add_days(d, -1)
    raise RuntimeError("no VHI item")


def vhi_season(end_day, bbox, W, H):
    y = end_day[:4]
    frm, to = y + "-04-01", min(end_day, y + "-10-31")
    ids = vhi_items(frm, to) if to >= frm else []
    fm = read_grid(vhi_url(vhi_newest()), bbox, W, H, 255)[0] != 255
    dfc = np.zeros((H, W), np.float32)
    ext = np.zeros((H, W), np.uint16)
    days = np.zeros((H, W), np.uint16)
    for i in ids:
        a = read_grid(vhi_url(i), bbox, W, H, 255)
        if a is None:
            continue
        v = a[0]
        ok = (v <= 100) & fm
        days += ok
        dfc += np.where(ok & (v < 40), 40 - v, 0).astype(np.float32)
        ext += ok & (v < 10)
    return dict(def_=dfc, ext=ext, days=days, ids=ids)


def season_tile(meta, lid, s, scenes, bbox, W, H):
    r = vhi_season(scenes[0][:10], bbox, W, H)
    L = meta["L"][lid]
    img = np.zeros((H, W, 4), np.uint8)
    sel = r["days"] > 0
    if lid == "vhidef":
        stops, (d0, d1) = L["rampStops"], L["domain"]
        k2 = (d1 - d0) / ((s["max"] - s["min"]) or 1e-9)
        rgb, fin = ramp_rgb(stops, d0 + (r["def_"].astype(np.float64) - s["min"]) * k2)
        vals = np.where(sel, r["def_"], np.nan).astype(np.float32)
    else:
        rgb = np.zeros((H, W, 3))
        done = np.zeros((H, W), bool)
        for thr, col, _ in L["classify"]:
            thr = np.inf if thr is None else thr
            m = ~done & (r["ext"] <= thr)
            rgb[m] = col
            done |= m
        vals = np.where(sel, r["ext"], np.nan).astype(np.float32)
    img[sel, :3] = u8(rgb[sel])
    img[sel, 3] = 255
    return img, vals, r
