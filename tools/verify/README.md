# Layer verification against rasterio / GDAL

Checks every layer of `swisseo-browser.html` in three ways:

1. **Regression:** the page of a reference commit (default `7c5cece^`) against the working tree, and the working tree
   with the decode workers off (main-thread decoding, as under `file://`). Map tiles (`renderTile`) and values
   (`sampleAoi` / `winDiff`, as in the TIFF-32 download) must be bit-identical.
2. **Web vs rasterio:** the same tiles computed independently with rasterio / GDAL and numpy (`ref.py`), same
   sampling rule (overview ≤ 1.35 × target pixel, nearest pixel centre), formulas, masks and colours.
   The forest disturbance classes use the original Sentinel Hub script in QuickJS (`special.py`). The VHI map colours
   come from the WMS and are checked against the COG values (`special.py --vhi`).
3. **Descriptions:** each index on land-cover classes of the scene (SCL), the forest mask and lakes (`semantics.py`).

Map display (MapLibre): `mapshots.py` compares screenshots of old and new at several zooms.

```bash
python3 tools/verify/serve.py &                                  # serves new.html, old.html, new-noworker.html on :8766
for p in new old new-noworker; do python3 tools/verify/drive.py --out OUT/web --pages $p & done; wait
python3 tools/verify/compare.py --web OUT/web                     # -> OUT/compare.json
python3 tools/verify/special.py --web OUT/web                     # forest disturbance -> OUT/special.json
python3 tools/verify/special.py --vhi --web OUT/web               # VHI COG and WMS -> OUT/vhi.json
python3 tools/verify/semantics.py --web OUT/web                   # descriptions -> OUT/semantics.json
python3 tools/verify/mapshots.py --out OUT/mapshots               # map display old vs new
python3 tools/verify/summary.py OUT                               # table per layer
```

Needs Python 3 with rasterio, numpy, scipy, Pillow and Selenium, Firefox (headless, WebGL), `qjs` (QuickJS) and the
network (data.geo.admin.ch, cms.geo.admin.ch, zhc-c.s3.cloud.switch.ch, the S3 vegetation masks, wms.geo.admin.ch). The test tiles and dates
are in `drive.py` (`TILES`). The page files are not changed: `serve.py` appends the hook (`hook.js`) when serving.
