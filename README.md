# swissEO Browser `BETA`

A minimal, browser-only viewer for swisstopo's **swissEO** satellite products, modelled on the
[Copernicus Browser](https://browser.dataspace.copernicus.eu/) workflow.

**Integration version (for testing): <https://swisstopo.github.io/topo-swisseobrowser/>**
It carries a red bar at the top and is **not for operational use**. The production version will be
`swisseobrowser.swisstopo.admin.ch`; it is not yet communicated and not yet reachable.

[![Ask DeepWiki](https://img.shields.io/badge/DeepWiki-Ask%20about%20this%20repo-003F6B)](https://deepwiki.com/swisstopo/topo-swisseobrowser)
**Search and ask questions about this repository:** [DeepWiki](https://deepwiki.com/swisstopo/topo-swisseobrowser)
generates browsable documentation from the code and this README and answers questions about them.

> **Not for operational use.** This is an experimental beta prototype: values, renderings and statistics
> are computed in the browser, are not validated and may be wrong or incomplete. For authoritative data use
> the swisstopo products and services directly. Every layer is being checked in depth; see
> [Layer verification](#layer-verification).
>
> Please note that AI (Claude Code with the Opus 5.5 model, medium effort) was used extensively to prepare this
> website, adapting it from the Copernicus Browser. The indices were edited and tested manually in QGIS or with
> rasterio and GDAL.

The whole application is a single file: [`swisseo-browser.html`](swisseo-browser.html). There is no
build step, no backend and no login. The page reads the swissEO Cloud Optimized GeoTIFFs (COGs) and
the swisstopo WMS/WMTS services directly in the browser.

> **About the rest of this repository:** this repo started as a clone of
> [eu-cdse/copernicus-browser](https://github.com/eu-cdse/copernicus-browser). All files other than
> `swisseo-browser.html` (`src/`, `public/`, `package.json`, …) are the upstream Copernicus Browser
> sources. They are kept **only as a reference** for its user-interface behaviour and are not built,
> used or modified by the swissEO Browser. Changes are pushed to this repository only, never upstream.
> For the Copernicus Browser itself, see the [upstream README](https://github.com/eu-cdse/copernicus-browser#readme).

## Data

| Product | Source | Used for |
| --- | --- | --- |
| [swissEO S2-SR v200](https://www.swisstopo.admin.ch/en/satelliteimage-swisseo-s2-sr) | COGs on `data.geo.admin.ch`, catalogue via the STAC API `data.geo.admin.ch/api/stac/v0.9` (collection `ch.swisstopo.swisseo_s2-sr_v200`) | Sentinel-2 L2A surface reflectance mosaics (B01–B12, B8A, AOT, SCL, cloud mask, terrain mask, true color image TCI), 10/20/60 m, LV95 |
| [swissEO VHI v100](https://www.swisstopo.admin.ch/en/satelliteimage-swisseo-vhi) | Own collection: `wms.geo.admin.ch` (`ch.swisstopo.swisseo_vhi_v100`, `…_vegetation`) for display; for AOI statistics and analytical downloads the `forest-10m` / `vegetation-10m` COGs, addressed through the STAC items of `ch.swisstopo.swisseo_vhi_v100` | Vegetation Health Index for forest and all vegetation, relative to 1991–2020; the daily `forest-10m` COGs also feed the VHI season layers (cumulative deficit, days in extreme stress) |
| [swissEO NDVIdiff v100](https://www.swisstopo.admin.ch/en/satelliteimage-swisseo-ndvidiff) | `forest-10m` COGs of the STAC collection `ch.swisstopo.swisseo_ndvi_diff_v100` | NDVI change of the current year compared to the previous year, forest perimeter, 10 m; one product for the end of July, August and September each year (since 2018) |
| [swissEO NDVIz v100](https://www.swisstopo.admin.ch/en/satelliteimage-swisseo-ndviz) | `forest-10m` COGs of the STAC collection `ch.swisstopo.swisseo_ndvi_z_v100` | NDVI anomaly as z-score, forest perimeter, 10 m; end of July, August and September (since 2017) |
| swissEO NDVIdiff v200 **BETA** | 30 example COGs on `cms.geo.admin.ch/Topo/umweltbeobachtung/beispiele/NDVIDIFFV2/` (not in STAC; the item list is in the page) | Year-on-year NDVI change of two-month first-quartile cloud-free mosaics of S2-SR v200 (June/July, July/August, August/September, 2017–2026), forest, 10 m |
| Vegetation masks | Habitat map COGs v1-0 / v1-1 / v1-2 (forest, all vegetation) in `s3-topo-satromo-prod` (`data/MASKS/Vegetation/`, as used by the VHI processor), inside = value ≠ 0; the swissTLM3D forest (`wms.geo.admin.ch`, `ch.swisstopo.swisstlm3d-wald`); Forest Type NFI 2023 (WSL, probability of broadleaf trees per 10 m pixel for all vegetation above 3 m, Float32 COG in `s3-topo-satromo-prod` (`data/MASKS/Vegetation/waldmischungsgrad_2023_10m_2056_cog.tif`); Waser et al. 2025, [doi:10.16904/1000001.7](https://doi.org/10.16904/1000001.7)); the ETH tree species maps (broadleaf basal-area share and dominant species, 30 m, `ETH_forest_leaf_type_share_01_broadleaved.tif` and `ETH_forest_species_argmax.tif` in the same folder; Zhou et al. 2026, [arXiv:2611.08095](https://arxiv.org/abs/2611.08095), CC BY-NC 4.0); the agricultural land use (Nutzungsflächen, BLW from the data of the cantons, `wms.geo.admin.ch` layer `ch.blw.landwirtschaftliche-nutzungsflaechen`; [metadata on geocat.ch](https://www.geocat.ch/datahub/dataset/ae183bc4-5c91-467e-89bc-85f390340efb)) | Forest, vegetation, broadleaf / conifer or land-use mask for every S2-SR layer, statistics and exports |
| Basemaps | `wmts.geo.admin.ch` (pixelkarte-farbe, swissimage, pixelkarte-grau) | Background maps *Map*, *SWISSIMAGE* and *Map Grey* on the native LV95 grid |
| 3D terrain | [swissALTIRegio](https://www.swisstopo.admin.ch/en/height-model-swissaltiregio): one COG on `data.geo.admin.ch` (STAC collection `ch.swisstopo.swissaltiregio`), 10 m, LV95, Switzerland and its border regions ([metadata on geocat.ch](https://www.geocat.ch/datahub/dataset/f7f058e9-288b-4c55-8f4e-6360880dbb59)); the surface model [swissSURFACE3D](https://www.swisstopo.admin.ch/en/height-model-swisssurface3d) resampled to 10 m, one COG in `s3-topo-satromo-prod` (`data/DSM/DSM_10m_EPSG2056_CH_clipped_10km_extended_9999_cog.tif`, Switzerland plus 10 km, no data −9999) | Heights of the optional 3D mode |
| Labels | `vectortiles.geo.admin.ch`: swisstopo's base map vector tiles (`ch.swisstopo.base.vt`, Switzerland and Liechtenstein) with the label layers of its imagery base map style | *Labels*: place, road, peak and lake names above the data |
| Place search | `api3.geo.admin.ch/rest/services/ech/SearchServer` with `type=locations`, as `searchLocation` in [web-mapviewer `search.api.js`](https://github.com/geoadmin/web-mapviewer/blob/3e5a2900/packages/mapviewer/src/api/search.api.js) | Municipalities, districts, cantons, place names and addresses |
| WMS / WMTS | `wms.geo.admin.ch` (preset) and the external providers of map.geo.admin.ch ([`external-providers.json`](https://github.com/geoadmin/web-mapviewer/blob/3e5a2900/packages/mapviewer/src/modules/menu/components/advancedTools/ImportCatalogue/external-providers.json), read when the panel is opened), or any WMS / WMTS URL | Layers of other map services on the map and in the compare list |

The map runs in **EPSG:2056 (CH1903+ / LV95)**, the native CRS of the basemaps and the COGs, so nothing
is reprojected. It is drawn with [MapLibre GL JS](https://maplibre.org/) and its custom projections
(`addProjection`, experimental, pinned to 6.16.0). MapLibre needs a power-of-two tile grid, which the swisstopo
WMTS levels are not, so the map has its own: tile 0/0/0 is a 512 px square at 2560 m/px with its top-left corner at
the swisstopo origin (2,420,000 / 1,350,000), so zoom 8 is exactly 10 m/px and every level lines up with the 10 m
pixel grid of the Sentinel-2 bands. The page draws every tile of this grid itself (custom `swisseo://` protocol):
the swisstopo WMTS tiles of the nearest level are composed into it, the swissEO layers are rendered from the COGs,
the VHI layers and external services are read by WMS or WMTS. At 20, 10, 5 and 2.5 m/px the swissEO layers are
pixel for pixel those of the swisstopo grid. The basemaps are composed from the swisstopo level nearest to the view's
resolution, each tile at that level's own pixel size, so only the GPU resamples them: at the resolution of a level the
map is shown 1:1 (pixel for pixel as before at 20, 5, 2, 1 and 0.5 m/px, within a sub-pixel shift at the others);
between the levels it is scaled, as any raster map in a continuously zooming viewer. The `zoom` of links stays the level of the swisstopo grid (see [URL parameters](#url-parameters)).

### Vegetation masks

The vegetation mask option (a pull-down, "Choose one" when off) restricts every S2-SR layer, the AOI statistics,
time series and spectral explorer, and the analytical and print exports. Its entries, in this order:

- **Habitat Map** (forest or all vegetation; one entry since
  [#9](https://github.com/swisstopo/topo-swisseobrowser/issues/9)): the habitat map that swissEO VHI uses on the date
  of the data, chosen as in `step1_processor_vhi.py` of
  [topo-satromo-v2](https://github.com/swisstopo/topo-satromo-v2) (`PRODUCT_VHI["vegetation_masks"]`): v1-0 (2022,
  CLC+ 2021) before 2024-07-12, v1-1 (2024, CLC+ 2023) before 2025-12-11, v1-2 (2025, CLC+ 2023) since. A time series
  takes the map of each date; the two-date layers take the map of the selected date on both dates. The small text
  under the mask names the version in use. They are COGs on the swissEO 10 m grid at
  `https://s3-topo-satromo-prod.s3.eu-central-1.amazonaws.com/data/MASKS/Vegetation/{forest|vegetation}_mask_2056_habitatv1-…tif`
  (CORS enabled), *inside = value ≠ 0*. Source: swisstopo, swissEO VHI processor.
- **swissTLM3D forest**: the WMS layer `ch.swisstopo.swisstlm3d-wald`, with check boxes for its classes Wald, Wald
  offen and Gebüschwald (any combination). The layer is drawn opaque, one colour per class, so *inside = alpha ≥ 128*
  of the GetMap image (all classes) or the nearest class colour; the pixel inspector gives the class (GetFeatureInfo).
  Source: [swissTLM3D](https://www.swisstopo.admin.ch/en/landscape-model-swisstlm3d), swisstopo.
- **Forest Type NFI 2023** (WSL; until November 2026 the Waldmischungsgrad LFI of data.geo.admin.ch): the
  **probability of broadleaf trees** per 10 m pixel (0–100 %), not a share of broadleaf trees, for all vegetation above
  3 m, not clipped to a forest mask. It comes from a Random Forest classification of Sentinel-1 and -2 data of 2021 to
  2023 with the swissALTI3D terrain model (overall accuracy 0.96, kappa 0.94; in mixed stands against the aerial image
  interpretation of the NFI 0.81). Larch counts as conifer. Yearly updates are planned from 2027. COG:
  `https://s3-topo-satromo-prod.s3.eu-central-1.amazonaws.com/data/MASKS/Vegetation/waldmischungsgrad_2023_10m_2056_cog.tif`
  (Float32, DEFLATE with the floating-point predictor, no data −3.4e38; read by geotiff.js exactly as by GDAL).
  - Three entries: *Conifer forest (Nadelwald, incl. larch)*, *Mixed forest (Mischwald)* and *Broadleaf forest
    (Laubwald)*. A slider with two handles sets the limits on 0–100 %: conifer at or below the first (**30 %** by
    default), mixed up to the second (**85 %**, the LFI's pure broadleaf), broadleaf above it. The limits are applied
    when a handle is released and kept when switching between the three entries.
  - *Mean of 3 × 3 pixels before the classes* (off by default): the LFI recommends it in mixed stands (values around
    50 %). The mean of the valid values of the 3 × 3 pixels of the native raster around the pixel under each cell is
    used on grids up to 1.5 native pixels (15 m); coarser grids read the overviews of the COG, which are averages already.
  - *Within*: the probability counts only inside a forest mask chosen independently, as the WSL suggests (forest mask AND
    class of the probability): the **forest of the habitat map of the date** (default, the version as for the habitat
    map entry), the **swissTLM3D forest** (all classes) or **none** (all vegetation above 3 m).
  - The link writes `lfi-conif:30.85` / `lfi-mixed:30.85` / `lfi-broad:30.85` (lower.upper limit), `:m3` for the 3 × 3
    mean and `+tlm` / `+none` for the forest mask. Older values with one number open too: `lfi-broad:76` with the upper
    limit 76, `lfi-conif:40` with the lower limit 40.
  - Check (2 × 2 km Sihlwald, statistics at 10 m against numpy on the COGs): conifer 3,226, mixed 7,732, broadleaf 22,197
    cells without forest mask (together all 33,155 valid cells), broadleaf with 3 × 3 mean 20,738, mixed within the
    habitat map forest v1-2 6,279: equal in every case.
- **ETH tree species** (30 m): two maps of the tree species composition of Switzerland by the ETH Zürich, trained on the
  basal areas of 3,992 plots of the National Forest Inventory (30 × 30 m) with aerial images, airborne laser scanning,
  satellite embeddings and climate data (macro-R² 0.485 over 11 classes in spatial cross-validation; on an independent
  forest-reserve dataset the dominant class right in 73.2 % of the pixels). COGs on the swissEO bucket next to the
  habitat maps: `ETH_forest_leaf_type_share_01_broadleaved.tif` (Float32, broadleaf share of the basal area 0–1) and
  `ETH_forest_species_argmax.tif` (Byte, the class with the largest predicted basal-area share). Non-forest pixels are
  left out by an internal mask, which the page uses for validity (a masked pixel never counts as 0 % broadleaf). The
  30 m grid starts at E 2'485'435 / N 1'295'915, 5 m off the 10 m grid: each 10 m cell takes the ETH pixel under its
  centre, and a cell centred on a pixel edge (every third one) the right / lower pixel. There is no further forest mask.
  - *Conifer / Mixed / Broadleaf forest*: the same two-handle slider (30 / 85 % by default) and 3 × 3 option as for Forest
    Type NFI, on the **broadleaf share** (a share, not a probability, so the limits are not directly comparable); the
    3 × 3 mean covers 3 × 3 ETH pixels (90 m). Link `eth-mixed:30.85`, `:m3`.
  - *Dominant tree species*: check boxes for the 11 classes in the colours of the file: Spruce (Fichte), Fir (Tanne),
    Pine (Föhre), Larch (Lärche), Arolla pine (Arve), Beech (Buche), Maple (Ahorn), Ash (Esche), Oak (Eiche), Chestnut
    (Kastanie), Other (Andere); *All conifers*, *All broadleaves* and *All* set them at once. Link `eth-sp` or `eth-sp:1.2.6`.
  - Check (the same 2 × 2 km square against numpy with rasterio on the COGs and their masks): conifer 3,330, mixed
    8,137, broadleaf 22,829 (together all 34,296 ETH forest cells), mixed with 3 × 3 mean 13,978, beech 23,138, spruce
    and fir 6,891: equal in every case.
  - The pixel inspector shows the broadleaf share and the dominant species at every spot.
  - Licence **CC BY-NC 4.0**: non-commercial use only, with attribution. Source: Zhou, Y.; Ferrari, L.; Griess, V. C.; Rehush, N.; Schindler, K.; Beloiu, M. (2026): *National-scale mapping of tree species composition in Switzerland from high-resolution aerial imagery and multimodal data*. [arXiv:2611.08095](https://arxiv.org/abs/2611.08095) (preprint). A 10 m version would
    be possible (about two weeks of work, with compromises); the 30 m version is used for now.
  - Source: Waser, L.; Ginzler, C.; Psomas, A.; Rüetschi, M.; Rehush, N. (2025): *Forest Type NFI*. National Forest Inventory (NFI). [doi:10.16904/1000001.7](https://doi.org/10.16904/1000001.7); funded by the Federal Office for the Environment (BAFU).
- **Nutzungsflächen** (agricultural land use, BLW from the data of the cantons; since
  [#16](https://github.com/swisstopo/topo-swisseobrowser/issues/16) the layer `ch.blw.landwirtschaftliche-nutzungsflaechen`
  of `wms.geo.admin.ch` instead of the geodienste.ch WMS): check boxes for the 13 main categories of its legend
  (Ackerfläche, Dauerwiesen, Dauerweiden, Reben, Obstanlagen, Übrige Dauerkulturen, Geschützter Anbau, Streueflächen,
  Hecken-, Feld- und Ufergehölze, Übrige Fläche innerhalb der LN, Sömmerungsfläche, Flächen ausserhalb der LN, Wald).
  The layer draws each category in its own colour and every parcel with a light-blue outline (102, 204, 255) of a fixed
  pixel width, which blends with the fills around it: read at 10 m, two thirds of the pixels are outline or blend. So
  the page reads the GetMap image at 2.5 m (4 × 4 samples per 10 m cell, majority; at most 4 × 4 per coarser cell): a
  pixel within 12 of a legend colour takes that category; outline pixels and blends take the most frequent category of
  their neighbours (repeated, so wider outlines fill from both sides), and an outline pixel with more empty than
  classed neighbours stays empty, as an outline on the edge of a parcel lies half outside it. Tests against the
  polygons of the WFS of the same cantonal data (2025) in 2 × 2 km squares: Fribourg (Kerzers) Ackerfläche +1.5 %,
  Dauerwiesen +0.1 %, Dauerweiden +3.4 %; Zurich +0.9 %, −0.2 %, +3.0 %. The federal layer also draws zoomed out and
  covers the cantons that do not publish on geodienste.ch (a 2 × 2 km square in Aargau: 62 ha of the three categories,
  none on geodienste.ch). The pixel inspector asks the service for the parcel (GetFeatureInfo: main category, use and
  code). Source: BLW, the cantons ([metadata on geocat.ch](https://www.geocat.ch/datahub/dataset/ae183bc4-5c91-467e-89bc-85f390340efb)).

The mask options in the layer menu link to the sources of Forest Type NFI (DOI), the ETH maps (arXiv) and the
Nutzungsflächen (geocat.ch).

The two-date layers use the mask of the selected date on both dates, so a new mask version never shows up as a
change. The VHI season sums keep the forest mask of swissEO VHI v100 itself (see below).

### Scaling and no-data

Physical value = DN × scale + offset, as documented in the swisstopo *Additional Content Information*
sheets ([S2-SR v200](https://www.swisstopo.admin.ch/dam/en/sd-web/-i2Y10KmboPf/swissEO_S2-SR_AdditionalContentInfo_v200.pdf),
[VHI](https://www.swisstopo.admin.ch/dam/en/sd-web/vtF6jZqH7L4V/swissEO_VHI_AdditionalContentInfo.pdf),
[NDVIdiff](https://www.swisstopo.admin.ch/dam/en/sd-web/bODfHY8ioFyS/swissEO_NDVIdiff_AdditionalContentInfo.pdf),
[NDVIz](https://www.swisstopo.admin.ch/dam/en/sd-web/mZTj7kABmTrD/swissEO_NDVIz_AdditionalContentInfo.pdf)):

| Asset | Scale | Offset | No-data / codes |
| --- | --- | --- | --- |
| B01–B12, B8A | 0.0001 | −0.1 | 0 |
| AOT | 0.001 | 0 | 0 |
| TCI (uint8 RGB) | 1 | 0 | 0 (the internal mask of the asset decides what is data) |
| SCL | 1 | 0 | 0 (Sen2Cor classes 1–11) |
| Cloud mask (OmniCloudMask) | 1 | 0 | 0 clear · 1 thick cloud · 2 thin cloud · 3 cloud shadow |
| Terrain mask | 1 | 0 | 0–180 solar incidence angle (°) · 200 shadow · 255 no data |
| VHI | 1 | 0 | 0–100 index · 110 no data (class) · 255 no data (raster) |
| NDVIdiff (int16) | 0.001 | 0 | 32700 missing data (shown grey) · 32701 no data |
| NDVIz (int16) | 0.01 | 0 | 32700 missing data (shown grey) · 32701 no data |
| NDVIdiff v200 BETA (int16) | 0.001 | 0 | 32701 no data (values −2000…2000) |

**NDVIdiff / NDVIz overviews:** the internal overviews of these COGs average the missing-data code 32700
into valid values (e.g. 31630 or −9395 in the overviews, while the full resolution stays within
−0.8…0.65 ΔNDVI). The browser therefore treats overview values outside |ΔNDVI| ≤ 1 and |z| ≤ 20 as no
data; at full resolution (zoomed in, or AOI statistics on a grid finer than 14.8 m) every value is used,
and the statistics then match a rasterio read of the COG exactly. The overviews should be rebuilt with
32700 excluded (e.g. as an additional no-data value or a mask). The NDVIdiff v200 BETA COGs have clean
overviews (no-data handled when they were built) and need no such filter.

Indices (NDVI, NDWI, …) are computed from ρ after this scaling. Very dark pixels can fall slightly below
0 after the −0.1 offset; such negative reflectance is set to 0 before an index is computed, so ratio
indices stay within −1…1.

**Why indices are higher than in the Copernicus Browser:** since processing baseline 04.00 the Sentinel-2
L2A digital numbers contain a +1000 shift, which the offset −0.1 removes. The Copernicus Browser requests
its data with Sentinel Hub's `harmonizeValues`, which is numerically equivalent to leaving the offset out,
so its NDVI over dense vegetation is markedly lower (e.g. 0.56 instead of 0.87). CDSE confirmed that the
offset is correct and recommends keeping it
([forum thread](https://forum.dataspace.copernicus.eu/t/sentinel-2-baseline-04-00-offset-csde-stac-derived-ndvi-doesnt-match-copernicus-browser-ndvi/5417)).
The swissEO Browser therefore always uses the physical reflectance.

## Features

- **Layout as in the Copernicus Browser**: the menu on the left has the Confederation logo of map.geo.admin.ch
  ([ConfederationFullLogo.vue](https://github.com/geoadmin/web-mapviewer/blob/3e5a2900/packages/mapviewer/src/modules/menu/components/header/ConfederationFullLogo.vue)),
  the language selector (EN, DE, FR, IT; see [Languages](#languages)), the collapse chevron and the title *swissEO Browser*; there is no header bar above the
  map. The chevron collapses the menu and a round button at the top left of the map opens it again; on small screens
  (up to 760 px) the menu starts collapsed and covers the map when opened. On the map:
  - top left: the date and the number of acquisitions on the map, the *Copy link* (chain) and *Pixel inspector* ((i) with a pointer) icon buttons;
  - top right, as in the Copernicus Browser: the place search, the basemap switcher (the layer button) and the
    **help button** (a plain *i*); below the *i* the area of interest, image download, compare, timelapse and *3D*
    buttons (in 3D also the 3D settings, sun shading and sun time);
  - bottom right: the zoom buttons and, on one line, the mouse position (LV95 easting and northing, `E 2'661'150 N 1'187'175`)
    and the scale bar; bottom left: the attribution and the loading indicator. The attribution names the data on the
    map ([#12](https://github.com/swisstopo/topo-swisseobrowser/issues/12)): swisstopo, the office of a vegetation mask
    from outside swisstopo (*Nutzungsflächen © BLW*, *Forest Type NFI © WSL / BAFU*, *ETH tree species © Zhou et al. 2026,
    CC BY-NC 4.0*) and the domain of a WMS /
    WMTS layer; MapLibre is credited in the Info tab and below.
- **Help and tutorial** ([`docs/index.html`](docs/index.html), opened by the (i) button in a new tab): an *About the
  swissEO Browser* overview with a beginner tutorial (Part A: window, place search, date, layers, vegetation mask, pixel
  inspector, area of interest and statistics, 3D, download, sharing) and all functions in the order of the
  [Copernicus Browser documentation](https://documentation.dataspace.copernicus.eu/Applications/Browser.html) (Part B:
  visualization with masks, vegetation masks and 3D visualization, tools, sharing, and the data with their sources and
  metadata links), with screenshots of the app in `docs/img/` (1400 × 900 px views, JPEG). Deployed with the page.
- **Basemap switcher** as in the Copernicus Browser: the layer button at the top right opens (on hover) *Basemaps* (*Map* =
  pixelkarte-farbe, *SWISSIMAGE*, *Map Grey* = pixelkarte-grau, *None*) and *Map overlays* (*Labels*, always drawn above
  the data).
- **Labels**: the place, road, peak and lake names of swisstopo's base map vector tiles, in the style of swisstopo's imagery
  base map (white text with a dark halo), drawn by MapLibre as text: sharp at every scale and on high-DPI screens,
  without overlaps, and upright and facing the viewer in 3D. The tiles are in Web Mercator, so MapLibre's workers fetch the
  Web Mercator tiles under each tile of the map's grid, move the label features into LV95 and encode them again
  (`swisseo-vt://`); the zoom levels of the style are shifted by the difference between the two grids at the latitude of
  Switzerland (about 4.39). The names stop at the border of Switzerland and Liechtenstein. The *Basic* image download
  takes them from the map; the high-res print and the timelapse, which are drawn away from the map, are without
  labels. The earlier ASIT VD label overlay was removed
  ([#6](https://github.com/swisstopo/topo-swisseobrowser/issues/6)): swisstopo is not an ASIT member.
- **3D terrain** (the *3D* button below the timelapse button): drapes the map, the data layers, the label overlay and
  the area of interest over **swissALTIRegio** ([metadata](https://www.geocat.ch/datahub/dataset/f7f058e9-288b-4c55-8f4e-6360880dbb59)), swisstopo's 10 m terrain model, read from its COG and turned into
  terrain tiles of the map grid in the browser (at most 20 m per pixel, about 6 s for a first view). In 3D the tools
  of the Copernicus Browser's 3D view are added above the others, as far as MapLibre supports them, and *3D* becomes
  *2D*:
  - **3D settings** (gear): the height model, *swissALTIRegio* (terrain, the default) or the *swissSURFACE3D* surface
    model at 10 m (with buildings and trees; its gaps and the area beyond it take swissALTIRegio's heights);
    *Sun shading* with its parameters (method, strength, shadow, highlight and accent colour, partly transparent over
    the image); *Vertical terrain scaling* (50–300 %); *Reset values*; links to the sources of the height models. A sky
    / atmosphere (MapLibre draws none here; the option was removed), shadows cast by mountains, a lens flare and
    anaglyph stereo of the Copernicus Browser are not available.
  - **Sun shading** (light bulb): a hillshade of the height model, lit from the direction and height of the sun at
    the map centre (NOAA formulas), above the data layers and below the labels.
  - **Sun time** (sun): date and time (UTC) of that sun, as sliders and fields, with the local time of the computer.
    By default, and again whenever 3D is switched on, it is the time of the scene shown
    ([#10](https://github.com/swisstopo/topo-swisseobrowser/issues/10)): the acquisition time of the S2-SR scene (UTC,
    from the item id), the middle between the acquisitions when the date has two orbits, and it follows the date and
    layer; for products without an acquisition time 10:30 UTC of the date. *Scene time* returns to it, *Current time*
    follows the clock, the sliders set a time of their own.

  Switching to 3D also switches the labels on ([#15](https://github.com/swisstopo/topo-swisseobrowser/issues/15)); back
  in 2D they stay on (the layer button switches them off). A link with `3d=true` keeps its own `labels` setting.

  In 3D the map can
  be tilted and turned (right-drag or Ctrl+drag, two fingers on touch screens, the compass above the zoom buttons
  resets it); the terrain beyond the basemaps takes the map's background colour. The split comparison needs the flat map, so 3D compares with opacity (switching 3D on turns a split into
  an opacity comparison; the highlights switch back to 2D). Statistics, analytical downloads, prints and the
  timelapse use the area around the centre of the view at its scale; the *Basic* download is the view as seen
  (without scale bar, an AOI crop clips all of it). The link keeps `3d`, `pitch`, `bearing`, `terrain` and
  `exaggeration`.
- **Place search** ("Go to Place", left of the basemap switcher, the width of the Copernicus Browser search field): the
  location search of map.geo.admin.ch, from two characters, results as you type (arrow keys and Enter work). A result
  zooms to its extent (municipality, district, canton) or to its point at the zoom of the result (1:25,000 when it has
  none, as on map.geo.admin.ch) and drops a pin; × clears the search and the pin. On small screens the field collapses
  to its magnifier icon.
- **Date selection as in Copernicus Browser**: a link without a date opens on the latest date with data;
  ‹ › jump to the previous / next date with data, the arrow button jumps to the latest one. The calendar,
  ‹ › and the grey "no data" date only consider acquisitions that **reach the map view**: the swath edge
  runs diagonally through each mosaic, so the data footprint of every relative orbit (`ORBIT_NR`) is read
  once from the coarsest B04 overview (≈ 640 m) and the calendar updates when the map moves.
  The calendar marks days with data, has month / year pull-downs and a maximum cloud-coverage slider
  (cloud cover of the whole mosaic, from its `metadata.json`, as the tile cloud cover in Copernicus). Several orbits acquired on the same day are mosaicked
  (most recent on top).
- **Configurations**: as the themes of the Copernicus Browser, the *Configuration* pull-down lists the
  layers for a task; each layer keeps its own data source, and the calendar shows the dates of the
  selected layer's source:
  - *Default*: composites (true color, false color, urban, SWIR, agriculture, geology), indices (NDVI,
    NDWI, moisture index, NDSI, NBR, AOT, **swissEO VHI** forest and vegetation, **swissEO NDVIdiff**),
    masks & quality (scene classification, cloud mask, terrain);
  - *Agriculture*: as the Copernicus Browser Agriculture theme, with the TCI as true color and without
    custom scripts: true color, false color, NDVI, EVI, Barren Soil, Moisture Stress, moisture index,
    agriculture, SAVI (colour steps and scripts of the Copernicus layers);
  - *Drought*: true color (TCI), NDVI, EVI, moisture index, swissEO VHI forest / vegetation, swissEO NDVIdiff,
    **swissEO NDVIdiff v200 BETA**, swissEO NDVIz, NDDI, NDDI change vs. the previous year and the NDVI difference to a reference date;
  - *Drought 2026*: like the Copernicus Browser *Drought and Floods* theme, with true color, moisture index,
    NDWI, Moisture Stress, NDVI, SWIR, urban and Highlight Optimized Natural Color, plus **highlights**;
  - *Forest*: true color (TCI), NDVI, EVI, swissEO VHI forest, **VHI cumulative deficit**, **VHI days in extreme
    stress**, swissEO NDVIdiff, swissEO NDVIdiff v200 BETA, swissEO NDVIz, NDVI difference to a reference date, Normalized Burn
    Ratio, moisture index and the **Forest Disturbance Classification**.
- **Highlights** (*Drought 2026*): story cards as in the Copernicus Browser (live thumbnail, title,
  dates, chevron). Clicking a card opens it on the map (the place at a fixed resolution and the TCI of the
  two dates as a split at 50 %, earlier date left, with a swipe handle) and the card turns blue; clicking
  another card switches. The chevron shows the text (English, at most ten lines), ending with *Show effects
  and advanced options*, which opens the compare settings. Choosing a layer leaves the highlight. Shared
  links reopen the highlight. Stories (defined in `CONFIGS.DROUGHT2026.highlights`: title, dates, layer,
  LV95 centre, m/px, text):

  | Story | Dates | Source of the text |
  | --- | --- | --- |
  | Baselland | 2026-05-23 ↔ 2026-07-04 | own |
  | Gürbetal and Aare valley | 2026-05-28 ↔ 2026-07-04 | [SRF Meteo](https://www.srf.ch/meteo/meteo-stories/trockenheit-in-der-schweiz-die-duerre-aus-der-vogelperspektive), 9 July 2026 (place identified from the SRF image) |
  | Great Aletsch Glacier | 2019-08-18 ↔ 2026-08-13 | [watson.ch](https://www.watson.ch/schweiz/klima/773592776-dieser-satellitenbilder-vergleich-zeigt-trockenheit-in-der-schweiz) |
  | Konstanz and Untersee, Zurich Airport, Forests near Brugg AG, Upper Lake Zurich, Wil SG, Lake Lucerne, Interlaken BE | 2025-08-08 ↔ 2026-08-08 | watson.ch, 10 August 2026 |
  | Lake Constance – Untersee | 2025-08-08 ↔ 2026-08-08 | [Blick](https://www.blick.ch/schweiz/ostschweiz/thurgau/untersee-faellt-auf-tiefsten-august-wert-seit-1930/49bvg7s), 12 August 2026 |
  | Lakes Neuchâtel and Murten | 2025-08-08 ↔ 2026-08-11 (no clear swissEO image on 8 August 2026 there) | watson.ch |
  | All of Switzerland | 2025-08-08 ↔ 2026-07-24 | watson.ch |

  The Tages-Anzeiger article on the same topic could not be read (paywall, archive not reachable).
- **Verification status**: every layer that has not yet been checked in depth carries the label **BETA** behind its name
  (in the layer list and the compare list), and its pull-down says that it still needs to be verified and that its values may
  be wrong; verified layers carry no label. See [Layer verification](#layer-verification).
- **Layers**: for S2-SR the true color, i.e. the **TCI** delivered with each mosaic (`tci_10m`, 8-bit RGB,
  JPEG / YCbCr) and shown as delivered (its internal mask decides what is data, so black pixels stay black),
  and the composites computed from the bands (false color, urban, SWIR, agriculture,
  geology 12-8-2, Barren Soil, Highlight Optimized Natural Color); NDVI, NDWI, moisture index, NDSI, NBR,
  AOT, EVI, SAVI, Moisture Stress, NDDI, Forest Disturbance Classification; scene classification, cloud mask,
  terrain / solar incidence.
  VHI: forest and vegetation (WMS), and the season sums VHI cumulative deficit and VHI days in extreme stress
  (from the daily forest COGs). Layers are listed with the Copernicus Browser preview thumbnails as icons.
- **Drought and forest layers**
  - *swissEO NDVIdiff* and *swissEO NDVIz* are read from their COGs with the colour ranges of the content
    information sheets (missing data grey). There are only three products per year (end of July, August,
    September), so the product **nearest to the selected date** is shown, also in compare, timelapse,
    statistics and exports; the date line names the product used.
  - *swissEO NDVIdiff v200 BETA*: beta data, not an official product. The year-on-year NDVI change of
    two-month **cloud-free mosaics** instead of single acquisitions. The mosaic
    ([main_cloudfree_mosaic_csde.py](https://github.com/swisstopo/topo-satromo-v2/blob/dev-20261006/main_functions/main_cloudfree_mosaic_csde.py))
    takes, per pixel and band (B02, B03, B04, B08), the first quartile of all observations of the window that
    are not cloud (mask 1–3), outside the footprint or in terrain shadow (200), as in the CDSE Sentinel-2
    quarterly mosaics; the windows are June/July, July/August and August/September
    ([util_reprocess_mosaic_csde.py](https://github.com/swisstopo/topo-satromo-v2/blob/dev-20261006/main_functions/util_reprocess_mosaic_csde.py)),
    named by their end date. NDVI from the mosaic reflectance minus the NDVI of the same window one year
    earlier ([test_reprocess_ndvidiff_csde.py](https://github.com/swisstopo/topo-satromo-v2/blob/dev-20261006/main_functions/test_reprocess_ndvidiff_csde.py)),
    clipped to forest. The window nearest to the selected date is shown; colours as swissEO NDVIdiff. Read
    with geotiff.js it matches a rasterio read exactly (test area near Aarau, 2026-08-31).
  - *NDDI* = (NDVI − NDWI) / (NDVI + NDWI), clipped to −1…1, with the palette of the
    [openEO drought notebook](https://github.com/Open-EO/openeo-community-examples/blob/main/python/50_thematic-notebooks/drought-nddi/drought-nddi.ipynb).
    By default the NDWI is computed from NIR and SWIR (B08, B11) as in
    [Gu et al. 2007](https://doi.org/10.1029/2006GL029127). The notebook (Awesome Spectral Indices) uses an
    NDWI from green and NIR (B03, B08); it is selectable as *Green*, with a warning: NDVI + NDWI is then
    close to zero over vegetation and the index saturates. Test over Aarau, 2026-07-04, cloud-free pixels:

    | NDWI | inside −1…1 | median | at +1 (vegetation, NDVI > 0.5) |
    | --- | --- | --- | --- |
    | green (notebook), with the −0.1 offset | 0.2 % | 19.5 | 86 % |
    | green (notebook), without the offset (DN / 10000) | 0.2 % | 23.2 | 100 % |
    | SWIR (Gu et al. 2007), with the offset | 74.5 % | 0.54 | 4 % |

    So the all-red map comes from the green NDWI, not from the reflectance offset.
  - *NDDI change vs. previous year*: NDDI of the date minus NDDI one year earlier (notebook palette,
    −1…1). The notebook compares May–July means of two years; here single dates are compared.
  - *VHI cumulative deficit* and *VHI days in extreme stress* (Forest): the
    two season indicators of the [Waldtrockenheit dashboard](https://waldtrockenheit-dashboard.vercel.app/vhi.html),
    which shows them per warning region, computed here **per pixel** from the daily swissEO VHI v100 forest
    COGs (10 m). For every day from 1 April to the selected day (at most 31 October), a VHI below 40
    (*stressed*) adds 40 − VHI to the deficit, and a VHI below 10 (*extremely stressed*) counts as a day in
    extreme stress (in total, not consecutively). Only days with a VHI value count (110 and 255 are
    skipped): after long cloudy periods the VHI is missing once its 7-day window has passed, so the deficit
    can be underestimated; the pixel inspector and the statistics give the number of days with data. Only
    pixels inside the forest mask of VHI v100 count (the mask of the most recent item; non-forest stays
    transparent): the overviews of the daily forest COGs of 2026-04-26 to 2026-05-08
    also hold values outside the forest (at 10 m their mask is the usual one), which would otherwise colour
    meadows and fields when zoomed out. The
    dashboard rates each region against its 2018–2025 climatology; per pixel this would need eight seasons
    of daily maps, so the deficit uses a fixed colour scale (0 to 2500, adjustable) and the extreme days the
    dashboard classes (0, 1–5, 6–15, 16–30, more than 30 days). The browser reads one COG per day: a
    regional view (6 tiles at 50 m) takes about 25 s the first time, a 2 × 2 km area at 10 m about 15 s.
    The sums are kept for the session, and a later day of the same season starts from those of an earlier
    one, so stepping forward through the dates or a timelapse only reads the days in between (31 August
    after 31 July: 4 s instead of 15 s; 27 weekly frames of a season at 480 px in 24 s). The AOI statistics
    show the histogram and the season curve (mean cumulative value over the area per day) instead of a
    time series. Checked against an independent rasterio read of the same 141 COGs (2 × 2 km near Aarau,
    1 April to 31 August 2026): the same sums of deficit, extreme days and days with data over all 40,000
    pixels, and the same values at the centre pixel (1509, 24 and 115).
  - *Forest Disturbance Classification*: the [Sentinel Hub custom script](https://custom-scripts.sentinel-hub.com/sentinel-2/forest_disturbance_classification/)
    by Jonas Viehweger and Martin Puhm (Joanneum Research, EvoLand project), run in the browser. A LightGBM
    model of 150 gradient-boosted trees classifies every pixel of a single date from B02, B05, B06, B8A, B11
    and B12 into bark beetle, clear cut, salvage logged (low confidence, same colour as clear cut), wildfire
    and windthrow; healthy forest is not drawn. Trained in Germany, Sweden and Spain (macro F1 0.83), valid
    only on forest, so the forest mask is on by default (clouds and cloud shadows are masked too). The trees
    (411 kB) are loaded on first use from jsDelivr, pinned to commit `0a071cf` of sentinel-hub/custom-scripts,
    and are only accepted when the code consists of tree functions alone. **Scaling:** the trees split on
    Sentinel Hub L2A digital numbers in the convention DN = 10000 × reflectance (data before processing
    baseline 04.00, e.g. the script's 2019 example), so the browser passes `max(0, DN − 1000)` of the swissEO
    bands, which equals 10000 × ρ. The port was checked against the original script (run in QuickJS): the same
    class for all 3000 test vectors. A 256 px tile takes about 0.2 s with the forest mask.
  - *NDVI difference to a reference date* (formerly *NDVI Analyst*): port of [RaffiBienz/ndvi_analyst](https://github.com/RaffiBienz/ndvi_analyst) (Canton of Aargau):
    ΔNDVI = NDVI(date) − NDVI(reference) (negative reflectance set to 0), forest mask by default, change =
    ΔNDVI below a threshold (default −0.08) followed by a 3 × 3 majority filter against edge effects.
    *Display*: the difference, or the detected change. The AOI statistics add the report of the original
    script: forest area, compared area and affected area in ha and %, with and without edge-effect removal.
    Both dates take, per pixel, the first clear scene (as the map). For a large AOI the report first uses a coarser
    grid (up to 320 cells across, read from the COG overviews) and warns that its shares can differ strongly from a
    10 m analysis; *Compute at 10 m* then processes the AOI at the full 10 m resolution in chunks of 1024 × 1024
    cells (exact areas and shares; checked against a rasterio computation). See
    [#5](https://github.com/swisstopo/topo-swisseobrowser/issues/5): for the Canton of Aargau the 176 m grid gave
    13.7 % (13 Aug 2026) and 7.4 % (12 Sep 2026) after edge removal (VHI v100 forest mask), 10 m gives 11.1 % and
    11.7 % (habitat map v1-2 forest mask; 11.9 % and 12.3 % with the VHI v100 mask in an independent rasterio run).
  - Reference of the two-date layers: the acquisitions within ±20 days of the same day one year earlier
    (or of a chosen reference date, which goes first), clearest first; up to six days form a per-pixel
    composite, each pixel taking the first acquisition that covers it without clouds, so orbit gaps and
    clouds are filled. Clouds and cloud shadows are masked on both sides by default.
- **Layer list**: clicking a layer shows it (check mark). Clicking the active layer again hides it, so
  only the background map is shown (no check mark, a hint above the list); one more click shows it again.
  The layer menu (legend, masks, effects) opens and closes with the chevron; on start it is closed unless
  the link opens it.
- **Layer pull-down**
  - the Copernicus Browser title, description and "More info" link (Sentinel Hub custom-scripts page;
    swisstopo product page for True color L2A and the swissEO-specific layers); `</>` shows the formula
    and scaling;
  - legend with adjustable colour scale (min / max); NDSI is rendered as in the Copernicus Browser (snow
    above an adjustable threshold in blue, true color elsewhere);
  - for the TCI, **dark scene edges are removed** whenever the day has more than one scene (orbit), without an option:
    some orbits have a dark strip along one swath edge, which covers the other scene of the day in a mosaic. As in
    [main_cloudfree_mosaic.py](https://github.com/swisstopo/topo-satromo-v2/blob/main/main_functions/main_cloudfree_mosaic.py)
    (edge margin 200 px, brightness 40), pixels within 2 km of the scene's real footprint edge whose mean
    RGB is below 40 count as no data, plus one 10 m pixel around them against the JPEG ringing of the hard
    transition; the next scene fills them. Where no other scene of the day has data (beyond the other swath, or along
    the outer limit of the mosaic beyond the border), the dark pixels stay
    ([#14](https://github.com/swisstopo/topo-swisseobrowser/issues/14): in November, with a low sun, 40 % of the pixels
    there are that dark and were left empty). The footprint comes from the TCI's internal mask at about 160 m;
    the edge zone is computed once per scene;
  - masks: clouds and cloud shadows (OmniCloudMask), terrain shadow (terrain mask 200), a vegetation
    mask (pull-down: off, forest or all vegetation of the habitat map swissEO VHI uses on the date, the swissTLM3D forest classes, conifer, mixed or broadleaf forest of Forest Type NFI 2023 or of the ETH tree species maps, the ETH dominant tree species, or
    Nutzungsflächen categories; see [Vegetation masks](#vegetation-masks)) and a **custom mask**: your own polygons
    (e.g. a forest map) loaded from a file or URL with the same import and limits as the area of interest;
    *Inside* keeps the data inside the polygons, *Outside* (inverted) the data outside. It works for every
    layer rendered from COGs (not the VHI WMS) and applies to the map, compare, AOI statistics, exports and
    the timelapse. After loading, the map zooms to the mask (a mask that comes with a shared link keeps the
    link's view). The layer pull-down shows the mask's file name, number of polygons and vertices, with
    *Replace* and *Remove*. A mask loaded from a URL is part of copied links, one from a file is not;
  - *effects and advanced options*: gain, gamma, red / green / blue ranges and opacity for all colour
    layers (for the TCI applied on top of the delivered image); for the composites computed from the bands
    also **Look**: *Standard* stretch or *True
    color optimized* (the tone curve of the Copernicus Browser True color layer: contrast enhancement with
    highlight compression, saturation 1.2, sRGB); gain, gamma, **adaptive gain** (lowers the gain when the
    view is bright (snow, glaciers, clouds) so that the 98th percentile of the reflectance stays just
    below saturation; never brightens, at most a factor of 4, recomputed when the view changes; not needed
    with the optimized look). Statistics, spectral explorer and pixel inspector use the reflectance bands
    also for true color; the inspector additionally shows the TCI value.
- **Compare**: add layers to the compare list; opening the Compare panel (or the ⇄ map button) shows
  them with a split or opacity effect, going back to Layers shows the single layer again. Reorder,
  remove and zoom to each entry (each titled with its layer name, prefixed by the data source only for
  the S2-SR layers). With the split effect a handle on the map swipes the top layer, with the
  date of each side next to it. **Each entry shows the date of the data it actually shows**, not the date it was added
  with: the nearest product for swissEO NDVIdiff, NDVIz and NDVIdiff v200 BETA (e.g. *2026-07-31* for a layer added on
  2026-08-13), the VHI day (the nearest one if the chosen day has none; also the end of the VHI season sums) or the
  S2-SR date (*no data* when there is none). The same date is used next to the swipe handle and in the image downloads.
- **WMS / WMTS** (button next to Compare in the configuration card, as the Copernicus Browser *WMS / WMTS* collection):
  - the swisstopo WMS (`https://wms.geo.admin.ch/?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities`, English titles) is
    preset and loaded when the panel opens; the pull-down above it lists the external providers of map.geo.admin.ch
    (`external-providers.json` of web-mapviewer, pinned to commit `3e5a2900`, fetched only when the panel is opened) and is
    searched by typing; **+** adds any other WMS or WMTS URL (a service URL or its GetCapabilities; without a
    type, `wmts` in the URL decides which protocol is tried first, then the other). The services you add are listed as
    buttons (with a delete button) and remembered in this browser;
  - the layers of the active service: search (*n of m layers*), pages of 10, 25, 50 or 100, a thumbnail (GetMap of the
    layer's extent within Switzerland, or one WMTS tile), title, abstract, attribution and *Metadata* links. A click shows
    the layer on the map instead of the swissEO layer (leaving the panel shows the swissEO layer again); the active layer
    has *Add to Compare* and a chevron that shows its legend, full description and opacity. Clicking the active layer
    again switches it off (the swissEO layer is shown again). The panel opens without an active layer (unless a link
    names one), and leaving it switches the external layer off;
  - drawing: from LV95 (EPSG:2056) when the service offers it, otherwise from LV03, Web Mercator, UTM 32N (EPSG:25832) or
    WGS84, placed on the LV95 tiles with an affine transform per 512 px tile (LV03 by the 2,000,000 / 1,000,000 m offset);
    WMS with one GetMap per tile, WMTS with the tiles of the tile matrix nearest to the resolution. Services that send no
    CORS headers cannot be shown: the map is drawn with WebGL, which only uses images sent with CORS headers (the status
    line and the layer's details say so);
  - permalink: `panel=wms` with `wmsUrl`, `wmsLayer` and `wmsOpacity`; external layers in the compare list keep their
    service URL, type and layer name in `compareLayers`.
- **Area of interest**: draw a rectangle (axis-aligned in LV95) or polygon, or import KML/KMZ, GPX, WKT,
  GeoJSON, a zipped Shapefile, an MGRS / GEOREF cell or a bounding box (WGS84, LV95 and LV03 coordinates
  are detected). Files can be uploaded or **loaded from a URL** (KML, KMZ, GPX, GeoJSON / JSON including API or
  WFS URLs returning GeoJSON, WKT, zipped Shapefile; the type comes from the extension, otherwise from
  the content; the server must allow cross-origin requests, CORS). **Sharing:** an area imported from a
  file or pasted is part of a copied link only when it is small (about 270 vertices; the link holds at
  most 8000 characters); the import dialog warns about this and the AOI bar shows *⚠ not in link*; an
  area loaded from a URL is shared as the URL (`aoiUrl`). Vertices stay editable (up to 2,000: drag a vertex, drag
  or click the middle of a side to add one, right-click a vertex to remove it; an edit or a new vertex that makes the
  outline cross itself is refused) and drawing again adds a polygon. The AOI is shown as an outline
  only; its toolbar copies the geometry, shows the area, centres the map and downloads the AOI as GeoJSON.
  For the area:
  - *Statistical info*: statistics and histogram for the selected date, and a time series over a date
    range (CSV download). The time series reads every date in the range (clouds are judged over the
    AOI itself, not by the cloud cover of the whole scene), least cloudy first (Stop keeps what has been
    read), and reports which dates were not reached by that day's orbit and which were fully masked. Clouds can additionally be excluded with the scene classification (SCL 3, 8, 9, 10),
    which catches clouds OmniCloudMask misses, and the area can be restricted to forest or to all
    vegetation (the share of valid pixels then refers to the masked area); a custom mask that is switched
    on for the layer restricts the area in the same way. VHI, NDVIdiff and NDVIz statistics are read from
    their COGs; the two-date layers report the difference (and the change
    report of the NDVI Analyst method) instead of a time series, the VHI season layers the season curve.
    For a large AOI the statistics use coarser grids read from the COG overviews: up to 320 cells across for the
    selected date, up to 140 for the time series (at least 10 m). Then one box right below the info line at the top
    ([#11](https://github.com/swisstopo/topo-swisseobrowser/issues/11)) names both grids, says what they mean and has one
    choice for both: **Fast (coarse grid)** or **Full resolution (10 m)**. At 10 m the AOI is processed in chunks of
    1024 × 1024 cells (two at a time, with the masks of the dialog), the selected date and every date of the time series
    (two dates at a time; Stop keeps the dates read). The result of the selected date has a **Download CSV** at either
    resolution (settings, resolution, cell counts, statistics and histogram; for class layers the cells, hectares and
    shares per class; for the NDVI difference the change report); the time series CSV has a column `grid_m`. At 10 m,
    counts, mean, standard deviation, minimum and maximum are exact; median and percentiles come from a histogram of
    4000 bins over the layer's value range (e.g. ±0.00025 for an index). An NDVI run over a 12 × 6 km AOI matched an
    independent rasterio computation (720,000 cells; mean, σ, minimum and maximum equal, median and percentiles within
    ±0.00025). The vegetation mask grids are kept (the last 24), so a series reads each mask once instead of once per
    date. The VHI season layers keep their season curve on the coarse grid.
  - *Spectral explorer*: mean surface reflectance of all 12 bands (± σ), with CSV download.
- **Image download**: three tabs as in the Copernicus Browser:
  - *Basic*: the current view as PNG or JPG, with captions (datasource, date, scale bar) and an optional
    description, map overlays, legend, crop to AOI and an optional AOI outline; works in compare mode and in 3D.
    It is copied from the map as drawn (basemap, data layers and overlay one after the other), so it shows
    exactly what is on screen.
  - *Analytical*: any layers of the collection (visualised) and raw bands (B01–B12, B8A, AOT, SCL, cloud
    mask, terrain mask; VHI values) for the current view or the AOI, at LOW / MEDIUM / HIGH (40 / 20 /
    10 m) or a custom resolution, up to 2500 × 2500 px, as PNG, JPG or GeoTIFF (8-bit, 16-bit = stored DN,
    32-bit float = index or physical value) in CH1903+ / LV95, optionally with a dataMask band. Several
    files are zipped.
  - *High-res print*: the view re-rendered for a printed size, with the same captions, legend and AOI options,
    as PNG or JPG ([#2](https://github.com/swisstopo/topo-swisseobrowser/issues/2)): width and height in cm,
    independent of each other, or a paper preset (A4 / A3, portrait / landscape), and DPI. *Scale*: *Fit*
    enlarges the view (or, with *Crop to AOI*, the area of interest) to the paper's aspect ratio, so it is always
    fully printed; a fixed scale (1:10 000 to 1:500 000) sets the extent to paper size × scale, centred on the
    area of interest (or the view), warns when the area does not fit (and gives the scale it needs) and adds the
    scale to the caption.
- **Timelapse**: as in the Copernicus Browser, for the current layer over the area of interest (data
  clipped to it, no outline drawn) or the current view:
  - time range, *Select 1 image per* orbit / day / week / month / year, month filter, Search;
  - **no hard limits**, e.g. one image per week over ten years. The search first reads the small scene
    metadata (about 4 kB each) and keeps only acquisitions whose orbit reaches the area (footprint per
    relative orbit); per week / month / year it then checks only the three clearest candidates (scene cloud
    cover) over the area. Example: Aletsch, weekly 2017 to 2026: 2,345 acquisitions, 1,304 checked, 505
    images in about two minutes. Above 600 checks or 300 frames the dialog warns that it takes a while
    and estimates the GIF size;
  - list of images with thumbnail (rendered only when the row scrolls into view), cloud cover and coverage
    of the timelapse area (AOI or view, computed from the cloud mask and the data footprint, not the cloud
    cover of the whole scene); per interval the image with the best coverage × clear sky is chosen; Max.
    cloud coverage and Min. tile coverage filter the list, images can be (de)selected;
  - frames are kept as JPEG (about 0.05 MB at 320 px, 0.2 to 0.5 MB at 1024 px instead of 4 MB of pixels)
    and decoded a few at a time, so hundreds of frames fit into memory;
  - preview player with speed (fps), transition None / Fade with fade duration, delay last frame,
    adaptive gain per frame for the band composites (snowy winter frames), legend and captions (date label,
    scale bar, source);
  - download as GIF or as video (MP4 or WebM, depending on the browser), default 1024 px (up to 2048).
    For long series a video is much smaller than a GIF (a GIF takes roughly 0.4 byte per pixel and frame);
    the video is recorded in real time, so 500 frames at 8 fps take about a minute. VHI layers work too
    (via the WMS; the VHI season layers from the COGs, which shows how the deficit builds up over a season).
- **Fast loading of the COGs**: JPEG tiles (the TCI) are decoded by the browser itself (about twice as
  fast as geotiff.js, off the main thread), decoded tiles are kept in a cache (up to 120 tiles), the map
  uses 512 px tiles like the COGs and keeps loading while panning, and a scene whose orbit misses a tile,
  or that the more recent scene already covers, is not read. Measured for the TCI of 2026-10-12: all tiles
  of a view in 1.0 to 1.5 s instead of 1.7 to 2.7 s.
- **Loading indicator**: at the bottom left, above the attribution, the number of tiles still rendering (or the basemap
  or terrain still loading) and of requests in flight; after 6 s of continuous loading it says that the connection is slow.
- **Pixel inspector**: the LV95 position, band values (DN and physical value), index value, SCL, cloud
  mask, terrain mask, forest / vegetation of the habitat map of the date (and of the layer's own mask), the
  swissTLM3D forest class, the broadleaf probability of Forest Type NFI, the broadleaf share and dominant species of the
  ETH maps and the Nutzungsflächen main category at
  a clicked location; for the two-date layers the index
  on both sides and the difference; for the Forest Disturbance Classification the class; for VHI,
  NDVIdiff, NDVIdiff v200 BETA and NDVIz the product value; for the VHI season layers the cumulative
  deficit, the days with VHI below 10 and the days with a VHI value.
- **Coordinates**: positions are LV95 (EPSG:2056) everywhere: the map centre in the permalink
  (`center=2703331.08,1133878.99`, as on map.geo.admin.ch), the mouse position at the bottom right, the compare entries,
  the pixel inspector, the area of interest in the link and the defaults of the import dialog. Links with the former `lat` / `lng`
  parameters open on the whole of Switzerland.
- **Permalink**: the URL is updated on every change (configuration, view, date, cloud filter, layer and
  whether it is shown, open layer menu,
  legend range, masks incl. the custom mask mode, look and effects, reference date, compare list including WMS / WMTS
  layers, the open WMS / WMTS service and layer, basemap and label overlay, AOI, 3D with tilt and direction); the *Copy link* icon (chain) at the top left of the map
  copies it. Areas and custom masks loaded from a URL are shared as that URL;
  areas imported from a file only when they are small, masks from a file never.
- **Feedback and issues** (Info tab, end of the *not for operational use* notice), as in
  [topo-drought-briefing](https://github.com/swisstopo/topo-drought-briefing): every message carries the **permalink of the
  current view** and a one-line summary of what is on the map (layer, id, date of its data, BETA; the compare list or the
  WMS / WMTS layer), so a sentence or two is enough. A local copy links to the same view on the public website.
  - *Feedback*: an e-mail to david.oesch@swisstopo.ch and joan.sturm@swisstopo.ch, opened in the mail app of the computer;
  - *Report an issue / improvement*: a new GitHub issue in this repository whose title and text the viewer writes
    (URL parameters `title` and `body`), with the permalink, the layer and, for problems, the browser already in it, and
    the choices as tick boxes: *Fix or change a layer*, *Change a text or translation*, *Report a general problem*,
    *Suggest an improvement*. The same four kinds are issue forms ([`.github/ISSUE_TEMPLATE`](.github/ISSUE_TEMPLATE)) for
    issues opened directly on GitHub, each with a required permalink field. Pre-filling the form fields from the URL
    did not work, hence the text; for it blank issues have to stay enabled (`config.yml`). Issues need a GitHub account,
    and *Issues* must be switched on in the repository settings.
- **Info tab**: four short cards. *Feedback* (the two ways to report something, with the privacy note), *Selected
  date* (the acquisitions of the selected date with their metadata), *How this works, data and scaling* (links to the
  help page and to this README, which describe the services, the scaling and no-data values, the formulas and the
  layer verification) and *Terms*. The explanations themselves live in the help page and here, so they exist once
  instead of three times.
- Colours follow the Swiss Confederation scheme used by
  [swisstopo/topo-drought-briefing](https://github.com/swisstopo/topo-drought-briefing).

## The catalogue

Two files decide what the application offers, and the deploy writes them into the page. They are the only
place to change it; the blocks they generate are marked in the page and in this README and are overwritten
on every deploy.

| File | What it decides |
| --- | --- |
| [`catalog/layers.yaml`](catalog/layers.yaml) | which layers exist and whether each is **verified**. Not verified means the BETA label on integration and not offered in production. |
| [`catalog/configurations.yaml`](catalog/configurations.yaml) | what the pull-down offers, in which order, with which layers in which groups, and whether a whole configuration is **beta** (integration only). |

The layer definitions themselves stay in `swisseo-browser.html`: bands, formulas, colour ramps and the
JavaScript of an index are code and belong there. The catalogue holds only the structure, so the same layer
can appear in several configurations and be held back everywhere at once.

```
python3 tools/build-catalog.py --env int --write-readme   # after editing catalog/: page + checklist
python3 tools/build-catalog.py --env int --check          # what CI runs
```

To see what a deploy would publish, [`tools/assemble-local.ps1`](tools/assemble-local.ps1) builds either
site locally, with the same steps as the workflows (on Windows; the deploys themselves run the same
commands on Linux):

```
powershell -File tools/assemble-local.ps1 -Env prod -Out _prod
cd _prod; python -m http.server 8000
```

It needs PyYAML (`python3 -m pip install "PyYAML==6.0.3"`; the workflows install the same pinned version).
It refuses a catalogue that names a layer the page does not define, a duplicate id, a configuration key
that is not a valid `themeId`, or a production build with no layers left, and it warns about a layer that
is in no configuration. Every id must be quoted in the YAML: `true` is a layer id, and YAML would
otherwise read it as a boolean.

## Layer verification

The layers are being checked one by one, in depth: data access (assets, dates, nearest product), scaling and
no-data, the formula and its source, masks, rendering and legend, statistics and exports, compared with
reference implementations where possible (GDAL / rasterio reads of the COGs, the original scripts). Until a
layer has passed this check it carries the label **BETA** behind its name, and its description says that it still
needs to be verified and links to this section; a verified layer carries no label.

**Tick a layer in [`catalog/layers.yaml`](catalog/layers.yaml)**, not in the checklist below: set
`verified: true` there and run

```
python3 tools/build-catalog.py --env int --write-readme
```

which regenerates both the checklist below and the configuration block of the page, then commit both.
The checklist is generated, and CI (`catalog-check.yml`) fails when it is edited by hand or does not
match the catalogue. Every deploy writes the ticked ids into the published page.

**A layer that is not ticked is not offered in production.** It carries the BETA label on the
integration version, where everything is visible for testing, and the production build leaves it out of
the configurations; a link that names it opens the default view and says that the layer is not available
in this version. The layer definitions stay in the file either way, so nothing changes about how a layer
works, only about where it is offered.

A local copy of `swisseo-browser.html` that was not deployed reads this README itself to find the ticks:
the copy next to the page when it is served from the repository, otherwise (for example opened as a file)
the README of `main` on GitHub.

<!-- verification:start -->
- [x] `true`: True color *(Default, Agriculture, Drought, Drought 2026, Forest)*
- [x] `nir`: False color *(Default, Agriculture)*
- [ ] `urban`: False color (urban) *(Default, Drought 2026)*
- [x] `swir`: SWIR *(Default, Drought 2026)*
- [ ] `agri`: Agriculture *(Default, Agriculture)*
- [ ] `geo`: Geology 12, 8, 2 *(Default)*
- [x] `ndvi`: NDVI *(Default, Agriculture, Drought, Drought 2026, Forest)*
- [ ] `ndwi`: NDWI *(Default, Drought 2026)*
- [ ] `ndmi`: Moisture index *(Default, Agriculture, Drought, Drought 2026, Forest)*
- [ ] `ndsi`: NDSI *(Default)*
- [ ] `nbr`: Normalized Burn Ratio (NBR) *(Default, Forest)*
- [ ] `aot`: Aerosol optical thickness *(Default)*
- [x] `scl`: Scene classification map *(Default)*
- [x] `cloud`: Cloud mask *(Default)*
- [x] `terrain`: Terrain / solar incidence *(Default)*
- [x] `vhi`: swissEO VHI forest *(Default, Drought, Forest)*
- [x] `vhiveg`: swissEO VHI vegetation *(Default, Drought)*
- [ ] `evi`: EVI *(Agriculture, Drought, Forest)*
- [ ] `savi`: SAVI *(Agriculture)*
- [ ] `barren`: Barren Soil *(Agriculture)*
- [ ] `mstress`: Moisture Stress *(Agriculture, Drought 2026)*
- [ ] `hon`: Highlight Optimized Natural Color *(Drought 2026)*
- [x] `ndvidiff`: swissEO NDVIdiff *(Default, Drought, Forest)*
- [x] `ndviz`: swissEO NDVIz *(Drought, Forest)*
- [ ] `ndvidiff2`: swissEO NDVIdiff v200 BETA *(Drought, Forest)*
- [x] `vhidef`: VHI cumulative deficit *(Forest)*, checked by FOEN
- [x] `vhiext`: VHI days in extreme stress *(Forest)*, checked by FOEN
- [ ] `fdc`: Forest Disturbance Classification *(Forest)*
- [ ] `nddi`: NDDI *(Drought)*
- [ ] `nddichg`: NDDI change vs. previous year *(Drought)*
- [ ] `analyst`: NDVI difference to a reference date *(Drought, Forest)*
<!-- verification:end -->

### Limits of the browser

Everything runs in the browser, so very large inputs are refused instead of freezing the page. Measured in
Firefox on a laptop:

| Input | Limit | Measured |
| --- | --- | --- |
| File size (upload or URL) | 50 MB | a 27.6 MB GeoJSON with 1,000,000 vertices is read and reprojected in 0.5 s (plus download time) |
| Area of interest | 100,000 vertices | 99,000 vertices: drawn in 2.5 s, rasterised for statistics in 0.2 s |
| Vertex editing of the AOI | 2,000 vertices | one edit handle per vertex; above this the area is shown without handles |
| Custom mask | 1,000,000 vertices | 20,000 polygons: 3 ms per 256 px tile at 10 m, 70–90 ms per tile when the whole country is in view |
| Area in a copied link | about 270 vertices | the geometry is written into the link only below 8000 characters; URL-loaded areas and masks are shared as their URL |

## Running it

Use the live version at <https://swisstopo.github.io/topo-swisseobrowser/>, or run it locally by serving the
folder with any static web server:

```bash
python -m http.server 8000
# then open http://localhost:8000/swisseo-browser.html
#   in German:      http://localhost:8000/swisseo-browser.html?lang=de
#   the help page:  http://localhost:8000/docs/index.html?lang=fr
```

A current desktop browser (Firefox, Chrome, Edge) with **WebGL2** is required: the map is drawn by MapLibre GL JS.
Browsers switch WebGL2 off on computers without a usable graphics card (virtual machines, remote desktop sessions;
Firefox reports `AllowWebgl2:false`). The page then says so in the map area. In Firefox, `about:config` →
`webgl.force-enabled` = `true` switches it on (software rendering, slower); in Chrome / Edge, *Use graphics
acceleration when available*. Opening the file directly (`file://`) works too, but only in English: a page
opened from disk cannot read the translation files, so serve the folder to see the other languages.

Conventions for further development (for people and for AI coding assistants) are in [`CLAUDE.md`](CLAUDE.md):
no em-dashes in any text, LV95 coordinates, pushes only to this repository, how to add a layer.

### Languages

The application and the help page are in **English, German, French and Italian**, with
[i18next](https://www.i18next.com/) (self-hosted in `lib/`, see the SBOM below) and a small shared script,
[`js/i18n.js`](js/i18n.js). The language comes from `?lang=` in the address, then from the earlier choice in this
browser (`localStorage`), then from the browser's own languages, else English. The selector at the top of the
menu (and in the header of the help page) switches without a reload: the map, the date, the layers, the
compare list and every other part of the address stay as they are, and the address gains `lang=`.

**Where the texts are.** English is the source and stays in the code: the text of every element marked with
`data-i18n` and the English argument of every `t("key", "English")` / `tn(...)` call in the page, plus the
English of the data the page renders (layer names, subtitles and descriptions, highlight stories,
configurations, class and mask labels). The translations are JSON files, one per language and page:

```
locales/en/app.json   locales/en/help.json     generated from the pages: never edit by hand
locales/de/app.json   locales/de/help.json     German (Swiss spelling: "ss", no "ß")
locales/fr/...        locales/it/...           French, Italian
```

Keys are readable and grouped by area (`status.lookingUp`, `layers.ndvi.description`, `classes.scl.4`,
`vocab.lnf.dw`, help blocks by section: `t3.p2`, `vis-masks.li4`). A missing key, a missing file or a failed
request shows the English, never a key or a blank; a page opened from disk stays English. Dates and numbers
on screen follow the language (`de-CH` 15.07.2026 and 12'345.6); exports, links and coordinates keep their
machine format. Not translated, by rule: product and collection ids, band names, index names (NDVI, VHI…),
COG, STAC, WMS, URLs, formulas and units. The titles and abstracts of the VHI layers are swisstopo's own, from
the GetCapabilities of wms.geo.admin.ch in each language; external WMS / WMTS services keep their titles. The
GitHub issue texts stay English, since the team reads them.

**Changing a translation.** Edit `locales/<lng>/<page>.json` and check it:

```bash
python tools/check-locales.py            # validate de, fr, it against the English
python tools/check-locales.py --extract  # after changing English in a page: regenerate locales/en
python tools/check-locales.py --check    # what CI runs: also fails when locales/en is stale
```

It reports invalid JSON, keys the English does not have, empty values, `{{placeholders}}` and HTML tags
that differ from the English, missing plural forms (French and Italian need `_one`, `_many` and `_other`) and
a German `ß` as errors, and keys still to translate and protected names missing from a translation as
warnings. To see a translation, serve the folder (`python -m http.server`) and open
`swisseo-browser.html?lang=de`; on non-production hosts every key missing in the current language is named
once in the browser console.

**Production** offers only the languages a native speaker has reviewed, today English and German. The list
is the line `offered='["en","de"]'` in [`deploy-prod.yml`](.github/workflows/deploy-prod.yml) (step *The
languages production offers*), which writes it into the page and the help page as `const LANGS_OFFERED`;
[`tools/assemble-local.ps1`](tools/assemble-local.ps1) reads the same line for a local production build. All
translation files are deployed anyway, and integration offers all four languages.

To offer **French or Italian** in production once a native speaker has reviewed it:

1. Check the translation on integration (`?lang=fr`, the help page included) and run
   `python tools/check-locales.py`: it must report no errors and no keys still to translate.
2. Add the language to that one line, e.g. `offered='["en","de","fr"]'` or `offered='["en","de","fr","it"]'`.
3. Optionally check the result locally: `powershell -File tools/assemble-local.ps1 -Env prod -Out _prod`
   (it runs `tools/check-dist.sh`, which fails if a file of an offered language is missing).
4. Commit on `int` and merge into `main` through the pull request; the production deploy does the rest.

Taking a language out again is the same edit in reverse. With one language the selector shows only EN.

**The help screenshots** are in `docs/img/` (English) and `docs/img/<lng>/` (the others, under the same
names); a missing one falls back to English. [`tools/screenshots/`](tools/screenshots/screenshots.mjs) takes all
22 views in every language from permalinks (`cd tools/screenshots && npm ci && npx playwright install chromium &&
node screenshots.mjs --lang de --only calendar`); after a change of the interface, reshoot the affected views.

**Adding a fifth language**, e.g. Romansh (`rm`):

1. Copy `locales/de/` to `locales/rm/` and translate both files (or start from the English files); run
   `python tools/check-locales.py` until it is clean. Romansh plurals use `_one` and `_other`.
2. In [`js/i18n.js`](js/i18n.js), add `rm` to `ALL`, its label to `NAMES` and its locale (`rm-CH`) to `LOCALE`.
3. In [`tools/check-locales.py`](tools/check-locales.py), add it to `LANGS` and its plural forms to `PLURALS`;
   add it to the list of offered languages in [`tools/check-dist.sh`](tools/check-dist.sh).
4. Take the screenshots: `node screenshots.mjs --lang rm`.

No other code changes: every text of the pages already goes through the keys.

### Deployment

Two environments, two branches:

- **Integration** <https://swisstopo.github.io/topo-swisseobrowser/> (GitHub Pages): published by
  [`.github/workflows/pages.yml`](.github/workflows/pages.yml) on every push to **`int`** that changes the page,
  this README, `docs/`, `lib/`, `js/`, `locales/` or `tools/`, and manually from the *Actions* tab. The repository's
  *Settings → Pages → Source* must be set to **GitHub Actions**.
- **Production** <https://swisseobrowser.swisstopo.admin.ch> (S3 bucket `s3-topo-satromo-swisseobrowser`,
  eu-central-1, behind CloudFront): published by
  [`.github/workflows/deploy-prod.yml`](.github/workflows/deploy-prod.yml) on every push to **`main`**, i.e. when
  `int` is merged into `main` through a reviewed pull request; repository admins can also start it manually.
  The workflow signs in to AWS with **OIDC** (no stored access keys; the IAM trust policy is limited to this
  repository and `main`), syncs the site to the bucket and invalidates the CloudFront cache. It needs two
  repository secrets, `AWS_ROLE_ARN` (the role to assume) and `CLOUDFRONT_DISTRIBUTION_ID`, and the
  repository variable `PROD_URL`, the public address the deploy checks afterwards (the CloudFront domain
  until the swisstopo domain is in place; without it the deploy runs and only that check is skipped).
  The subject this repository sends to AWS uses GitHub's *immutable* format, with the numeric owner and
  repository ids next to the names (`repo:<owner>@<id>/<repo>@<id>:ref:refs/heads/main`), so the trust
  policy of the role must contain exactly that string. The workflow prints the claims of its own token as
  an annotation and in the run summary before it calls AWS, which is the authoritative source if the
  trust ever has to be rebuilt.

Both deploys assemble the same site: `swisseo-browser.html` as `index.html`, this README, the help pages in
`docs/`, the self-hosted libraries in `lib/`, the language script `js/i18n.js`, the translations in `locales/`
and the layer thumbnails the page references from
`public/previews/`; the upstream Copernicus Browser sources are never published. Integration additionally
keeps the page under its own name, so older links to `swisseo-browser.html` still work there; production
serves it only as `index.html`. On every
deploy `tools/build-catalog.py` writes the catalogue of [`catalog/`](catalog/) into the page (the
configurations and the [layer verification](#layer-verification)) and `tools/check-dist.sh` verifies that
no library is loaded from a CDN and that the build matches its environment. All GitHub Actions are pinned
to commit SHAs.

The two builds differ in what they offer: integration carries every layer and every configuration, with
BETA labels on the ones that are not verified yet, and production carries only the verified layers and
the configurations that are not marked beta. The layer definitions remain in both files; what the
production build changes is the generated configuration block, which is the only place a layer is
offered, so a hidden layer cannot be reached through the interface or through a link.

Three things differ between the two environments:

- **The red bar at the top.** The page and the help page decide at load time from the host name: every
  environment except production carries it, which includes GitHub Pages, a local server and a copy opened
  as a file. The production hosts are the list in the small script in the head of both files; at go-live
  the CloudFront host can be dropped from it, and the sentence can name the production address.
- **Search engines.** The committed files look like production, and the Pages deploy replaces the
  `robots:marker` comment with `<meta name="robots" content="noindex, nofollow">`, so only integration is
  kept out of search results. A failure of that step can at worst let the integration version be indexed,
  never hide production. A `robots.txt` cannot do this here: on a project page it is served under
  `/topo-swisseobrowser/`, while crawlers read only the one at the root of `swisstopo.github.io`, which is
  a different repository.
- **The link preview.** The Open Graph tags (title, description and `docs/img/og-image.jpg`, a 1200 × 630
  view of the application) need absolute addresses. They are committed with the integration address, so a
  local copy previews correctly, and the production deploy rewrites them to `PROD_URL`. Without that
  variable the deploy only warns: the preview then shows the integration image.

`tools/check-dist.sh` takes the environment as its second argument (`int` or `prod`) and refuses a build
whose noindex tag, integration bar or preview image does not match it.

### Libraries (SBOM)

The page loads no code from third-party CDNs: the runtime libraries are self-hosted in `lib/`, generated by
[`tools/vendor/vendor.mjs`](tools/vendor/vendor.mjs) from the exact versions pinned in
[`tools/vendor/package.json`](tools/vendor/package.json) (`cd tools/vendor && npm ci && node vendor.mjs`).
The pinned CDN URLs remain in the page only as the fallback when it is opened as a lone local file without
the `lib/` folder. MapLibre GL JS is an ES module, so the page script is a module too; proj4, pbf,
vector-tile and vt-pbf also run inside MapLibre's workers. The decision trees of the Forest Disturbance
Classification are converted into a module as well, so the served page compiles no code at runtime and
works under a Content-Security-Policy without `'unsafe-eval'` (it needs `worker-src 'self' blob:`).

| Library | Version | Licence | Source | Used for |
| --- | --- | --- | --- | --- |
| [MapLibre GL JS](https://github.com/maplibre/maplibre-gl-js) | 6.17.0 | BSD-3-Clause | npm `maplibre-gl` | map and its workers |
| [proj4js](https://github.com/proj4js/proj4js) | 2.22.0 | MIT | npm `proj4` | LV95 coordinates, also in the workers |
| [geotiff.js](https://github.com/geotiffjs/geotiff.js) | 2.1.3 | MIT | npm `geotiff` | reading the COGs (held at 2.x, see [`dependabot.yml`](.github/dependabot.yml)) |
| [pbf](https://github.com/mapbox/pbf) | 5.1.2 | BSD-3-Clause | npm `pbf` | label tiles (workers) |
| [vector-tile](https://github.com/mapbox/vector-tile-js) | 3.0.0 | BSD-3-Clause | npm `@mapbox/vector-tile` | label tiles (workers) |
| [vt-pbf](https://github.com/maplibre/vt-pbf) | 4.3.3 | MIT | npm `@maplibre/vt-pbf` | label tiles (workers) |
| [togeojson](https://github.com/placemark/togeojson) | 7.1.3 | BSD-2-Clause | npm `@tmcw/togeojson` | KML / GPX import |
| [JSZip](https://github.com/Stuk/jszip) | 3.10.2 | MIT (dual MIT / GPL-3.0-or-later; used under MIT) | npm `jszip` | KMZ / Shapefile import |
| [shpjs](https://github.com/calvinmetcalf/shapefile-js) | 6.2.0 | MIT | npm `shpjs` | Shapefile import |
| [mgrs](https://github.com/proj4js/mgrs) | 2.2.0 | MIT | npm `mgrs` | MGRS grid references |
| [gifenc](https://github.com/mattdesl/gifenc) | 1.0.3 | MIT | npm `gifenc` | timelapse GIF export |
| [i18next](https://github.com/i18next/i18next) | 26.5.11 | MIT | npm `i18next` | languages of the page and the help page |
| [Forest Disturbance Classification](https://github.com/sentinel-hub/custom-scripts) | commit `0a071cf` | CC BY-SA 4.0 | sentinel-hub/custom-scripts (Joanneum Research, EvoLand) | `fdc` layer model, 150 decision trees converted to a module |
| [WMS / WMTS provider list](https://github.com/geoadmin/web-mapviewer) | commit `3e5a2900` | BSD-3-Clause | geoadmin/web-mapviewer | WMS / WMTS panel suggestions |

### Security

- **Protected branches**: `main` only changes through a reviewed pull request (no force pushes); production
  deploys therefore always carry a second pair of eyes. Manual production deploys additionally require the
  admin role on the repository.
- **Dependency alerts**: Dependabot watches the pinned GitHub Actions and the library versions in
  `tools/vendor/package.json` ([`.github/dependabot.yml`](.github/dependabot.yml)); CodeQL analyses the
  page's JavaScript weekly and on every push ([`.github/workflows/codeql.yml`](.github/workflows/codeql.yml)).
- **Two dependency manifests, only one of them shipped**: this repository still carries the upstream
  Copernicus Browser (`package.json` and `package-lock.json` at the root, around 2000 packages of a React
  build), kept as a reference and never built, never installed and never deployed. GitHub's dependency graph
  scans those files all the same, so most alerts on this repository point at them. Only alerts whose manifest
  is `tools/vendor/package.json` or `tools/vendor/package-lock.json` concern code that reaches users, and
  only the runtime dependencies there do: `esbuild` is a build tool that produces `lib/` on a developer
  machine. The upstream tree contains older copies of libraries that are also in `lib/` (for example
  `maplibre-gl` 1.15.3 against 6.17.0 in `lib/`), so an alert can name a library the site uses and still not
  apply to it. Check the version and the manifest path of the alert, then dismiss an upstream one as "not
  used" with that reason.
- **Vendored libraries are reproducible**: [`.github/workflows/vendor-check.yml`](.github/workflows/vendor-check.yml)
  rebuilds `lib/` from the pinned versions on every pull request that touches `lib/` or `tools/vendor/` and
  fails if the result differs, so nothing can be edited into `lib/` by hand. A Dependabot pull request that
  bumps a library is therefore only half the change: run `cd tools/vendor && npm ci && node vendor.mjs`, commit
  the new `lib/`, and update the file names in the `LIB_CDN` map of the page and in the SBOM table above.
- **Update process**: the application owner reviews new Dependabot and CodeQL alerts weekly and on
  notification. A critical vulnerability in a shipped library is fixed within 48 hours: bump the version in
  `tools/vendor/package.json`, regenerate `lib/`, update the `LIB_CDN` map in the page and the SBOM table
  above, verify on integration, then merge to `main` (which deploys to production). Non-critical updates go
  with the next regular release. Libraries change only through `tools/vendor`, never by editing `lib/`.

## URL parameters

Parameter names follow the Copernicus Browser where an equivalent exists.

| Parameter | Example | Meaning |
| --- | --- | --- |
| `lang` | `de` | Language: `en`, `de`, `fr`, `it` (of those the build offers); written only when it is not English, see [Languages](#languages) |
| `center` | `2703331.08,1133878.99` | Map centre in LV95 (E,N), as on map.geo.admin.ch |
| `zoom` | `17` | Zoom level of the swisstopo LV95 grid (8 to 27; about 17 to 18 for a region; fractional values give resolutions between the grid levels, interpolated in scale; written with three decimals) |
| `3d`, `pitch`, `bearing` | `true`, `60`, `160` | 3D terrain mode, with the tilt (0–75°) and the direction of view (degrees from north) |
| `terrain`, `exaggeration` | `dsm`, `1.5` | 3D height model (`alti` = swissALTIRegio, the default, or `dsm` = swissSURFACE3D 10 m) and vertical terrain scaling (0.5–3) |
| `fromTime`, `toTime` | `2026-10-05T00:00:00.000Z` | Selected date |
| `cloudCoverage` | `30` | Maximum cloud coverage in % |
| `layerMenu` | `open` | The menu of the active layer is open (default: closed) |
| `showLayer` | `false` | The active layer is hidden, only the background map is shown |
| `themeId` | `DROUGHT` | Configuration: `DEFAULT`, `AGRICULTURE`, `DROUGHT`, `DROUGHT2026`, `FOREST` (when missing or not containing the layer, the first configuration with the layer is used) |
| `layerId` | `ndvi` | `true`, `nir`, `urban`, `swir`, `agri`, `geo`, `barren`, `hon`, `ndvi`, `ndwi`, `ndmi`, `ndsi`, `nbr`, `aot`, `evi`, `savi`, `mstress`, `nddi`, `nddichg`, `analyst`, `fdc`, `scl`, `cloud`, `terrain` (S2-SR); `vhi`, `vhiveg` (VHI); `vhidef`, `vhiext` (VHI season sums); `ndvidiff`, `ndvidiff2` (v200 BETA), `ndviz` |
| `valueRange` | `[0,0.9]` | Colour-scale min/max of index and continuous layers |
| `threshold` | `0.5` | NDSI snow threshold (default 0.42; above it snow is shown in blue, otherwise true colour, as in the Copernicus Browser); NDVI difference to a reference date change threshold (default −0.08) |
| `refDate` | `2025-07-01` | Reference date of the two-date layers (default: the same day one year earlier) |
| `displayMode` | `change` | NDVI difference to a reference date display: `diff` (default) or `change` |
| `ndwi` | `green` | NDWI of the NDDI layers: `swir` (default, Gu et al. 2007) or `green` (openEO notebook) |
| `gain`, `gamma` | `1.2` | Effects for the composites (1 = default) |
| `autoGain` | `true` | Adaptive gain for the composites |
| `look` | `optimized` | *True color optimized* tone curve for the composites (default: standard stretch) |
| `redRange`, `greenRange`, `blueRange` | `[0,0.8]` | Advanced RGB effects |
| `opacity` | `70` | Layer opacity in % |
| `cloudMask`, `shadowMask`, `terrainMask` | `true` | Masks (written when they differ from the layer's default; the two-date layers mask clouds and shadows by default) |
| `vegetationMask` | `forest` | Vegetation mask of the S2-SR layers: `off`; `forest` or `vegetation` (the habitat map of the date, as swissEO VHI; older links with a version such as `forest@1-1` open with the map of the date too); `tlm` or `tlm:12.13` (swissTLM3D forest, all or some of the classes 12 Wald, 13 Wald offen, 6 Gebüschwald); `lfi-conif:30.85`, `lfi-mixed:30.85` or `lfi-broad:30.85` (Forest Type NFI 2023, conifer, mixed or broadleaf forest with the lower and upper limit of the broadleaf probability in %; optionally `:m3` for the mean of 3 × 3 pixels and `+tlm` or `+none` for the forest mask, default the habitat map forest of the date, e.g. `lfi-mixed:30.85:m3+tlm`; older values with one number such as `lfi-broad:85` open too); `eth-conif:30.85`, `eth-mixed:30.85` or `eth-broad:30.85` (ETH broadleaf basal-area share, optionally `:m3`); `eth-sp` or `eth-sp:1.2.6` (ETH dominant tree species, all or some of the codes 1 Spruce, 2 Fir, 3 Pine, 4 Larch, 5 Arolla pine, 6 Beech, 7 Maple, 8 Ash, 9 Oak, 10 Chestnut, 11 Other); `lnf` or `lnf:a.dw.dp` (Nutzungsflächen, all or some main categories: `a` Ackerfläche, `dw` Dauerwiesen, `dp` Dauerweiden, `r` Reben, `o` Obstanlagen, `dk` Übrige Dauerkulturen, `g` Geschützter Anbau, `s` Streueflächen, `h` Hecken-, Feld- und Ufergehölze, `u` Übrige Fläche innerhalb der LN, `so` Sömmerungsfläche, `v` Vegetation nicht LN, `w` Wald); the NDVI difference to a reference date layer and the Forest Disturbance Classification default to `forest` |
| `basemap`, `labels` | `swissimage`, `true` | Basemap (`pixelkarte` = *Map*, `swissimage`, `grey` = *Map Grey*, `none`) and the *Labels* overlay (swisstopo vector labels) |
| `compareLayers`, `comparedOpacity`, `comparedClipping`, `compareMode` | | Compare list (base64url JSON, each entry with its LV95 view; WMS / WMTS entries as `{"l":"ext","x":{"u":service URL,"k":"WMS"/"WMTS","n":layer name,"t":title}}`), per-layer opacity and split range; `compareMode` is `split` / `opacity` when comparing and `off` otherwise (links without it open in compare mode) |
| `panel` | `wms` | The WMS / WMTS panel is open |
| `wmsUrl`, `wmsLayer`, `wmsOpacity` | `https://wms.geo.admin.ch/?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities`, `ch.bafu.bundesinventare-bln`, `70` | Service of the WMS / WMTS panel (default: the swisstopo WMS), the layer shown from it and its opacity in % |
| `aoi` | | Area of interest as base64url GeoJSON geometry in LV95, 0.1 m (only areas up to about 270 vertices) |
| `aoiUrl` | `https://…/area.geojson` | Area of interest loaded from this URL (written instead of `aoi` when the area came from a URL and was not edited) |
| `maskUrl` | `https://…/forest.geojson` | Custom mask loaded from this URL |
| `customMask` | `in` | Custom mask of the layer: `in` (keep inside the polygons) or `out` (keep outside); needs a mask (`maskUrl` or loaded in the page) |

Example:
`swisseo-browser.html?zoom=17&center=2703331.08,1133878.99&fromTime=2026-10-05T00:00:00.000Z&toTime=2026-10-05T23:59:59.999Z&cloudCoverage=77&layerId=ndvi&valueRange=[0,0.9]`

## Limitations

- Not available compared with the Copernicus Browser: pins, product search and download, custom
  scripts, other satellite collections, sharing timelapses through a server; the image download has no
  OSM background and no choice of coordinate system (always LV95). The 3D mode has no sky / atmosphere, no shadows
  cast by mountains, no lens flare, no anaglyph stereo, no split comparison and no 3D timelapse.
- The map needs WebGL. Its custom projection API is experimental in MapLibre, so the page pins MapLibre 6.16.0.
- The ETH tree species masks have 30 m pixels (5 m off the 10 m grid) and are licensed CC BY-NC 4.0 (non-commercial use
  only); a 10 m version may follow. Their broadleaf basal-area share and the broadleaf probability of Forest Type NFI are
  different quantities, so the same limits on the slider do not give the same classes.
- The VHI forest and vegetation layers are rendered by the WMS with its published styling, so their colour scale cannot be changed.
- The VHI season layers sum only the days with a VHI value, so long cloudy periods lead to an underestimated
  deficit; they read one COG per day, so the first view of a season takes a while, and they are not
  rated against a climatology as in the Waldtrockenheit dashboard.
- NDVIdiff / NDVIz: see the note on their overviews above; zoomed out, implausible overview pixels are left out.
- NDDI and NDDI change compare single acquisitions, not the May–July means of the openEO notebook. With the
  notebook's green NDWI the NDDI saturates (see above); the default SWIR NDWI does not.
- The Forest Disturbance Classification is a single-date model trained outside Switzerland; expect
  misclassifications, use it on forest only and validate the results.
- The NDVI difference to a reference date layer (NDVI Analyst method) works on the swissEO S2-SR mosaics instead of the original script's own Sentinel-2
  processing.
- AOI statistics use a grid of at least 10 m (coarser for large areas, which the dialog states); the statistics of
  the selected date and the time series can be computed at 10 m for any layer and AOI size (*Full resolution (10 m)*),
  which takes longer (a 10 m time series of a large AOI several minutes).
- Statistics, time series, analytical downloads and high-res prints read the COGs in the browser; large
  areas, long date ranges and large prints take a while. Imports and custom masks have size limits (see
  *Limits of the browser*); areas and masks from files are not shared through links.
- swissEO NDVIdiff v200 BETA is beta data from example files outside STAC; its list of windows is fixed in the page.
- WMS / WMTS: only services that allow cross-origin requests (CORS) can be read, and only over HTTPS; layers that the
  service offers in none of LV95, LV03, Web Mercator, UTM 32N and WGS84 cannot be shown. Layers not in LV95 are placed on
  the LV95 grid per tile (accurate to about a pixel), not reprojected per pixel. Services whose images come without
  CORS headers cannot be shown at all (WebGL); the timelapse, statistics and pixel inspector only work with the swissEO layers.
  Only the default style and the default time of a layer are used.
- The French and Italian translations have not yet been reviewed by native speakers, so production offers
  English and German only (see [Languages](#languages)).

## Credits and terms

- Data © [swisstopo](https://www.swisstopo.admin.ch),
  [open government data](https://www.swisstopo.admin.ch/ogd-conditions). swissEO S2-SR and swissEO VHI
  contain modified Copernicus Sentinel data. 3D terrain: [swissALTIRegio](https://www.geocat.ch/datahub/dataset/f7f058e9-288b-4c55-8f4e-6360880dbb59) and swissSURFACE3D
  © swisstopo. Masks: [Forest Type NFI](https://doi.org/10.16904/1000001.7) © WSL (Waser et al. 2025, funded by the BAFU);
  [ETH tree species](https://arxiv.org/abs/2611.08095) © Zhou et al. 2026 (ETH Zürich), CC BY-NC 4.0 (non-commercial use only);
  [Nutzungsflächen](https://www.geocat.ch/datahub/dataset/ae183bc4-5c91-467e-89bc-85f390340efb) © BLW and the cantons. Layers of other WMS / WMTS services
  © their providers.
- User-interface workflow modelled on the [Copernicus Browser](https://browser.dataspace.copernicus.eu/)
  by the Copernicus Data Space Ecosystem ([eu-cdse/copernicus-browser](https://github.com/eu-cdse/copernicus-browser):
  themes, layer descriptions, preview thumbnails, layout, basemap switcher, WMS / WMTS panel and icons). This project is not affiliated with or endorsed by the
  Copernicus Data Space Ecosystem.
- Builds on: [swisstopo/topo-satromo-v2](https://github.com/swisstopo/topo-satromo-v2) (processing of the
  swissEO products; NDVIdiff v200 BETA from the `dev-20261006` branch; the dark-edge rule of
  `main_cloudfree_mosaic.py`), [swisstopo/topo-drought-briefing](https://github.com/swisstopo/topo-drought-briefing)
  (colour scheme), [geoadmin/web-mapviewer](https://github.com/geoadmin/web-mapviewer) (map.geo.admin.ch: location
  search, Confederation logo and Swiss flag, list of external WMS / WMTS providers), [RaffiBienz/ndvi_analyst](https://github.com/RaffiBienz/ndvi_analyst) (NDVI Analyst of
  the Canton of Aargau), [Open-EO/openeo-community-examples](https://github.com/Open-EO/openeo-community-examples)
  (NDDI drought notebook), the [Waldtrockenheit dashboard](https://waldtrockenheit-dashboard.vercel.app/vhi.html)
  (cumulative VHI deficit and days in extreme stress), [sentinel-hub/custom-scripts](https://github.com/sentinel-hub/custom-scripts)
  (index definitions and visualisations; Forest Disturbance Classification by Joanneum Research, EvoLand); libraries [MapLibre GL JS](https://github.com/maplibre/maplibre-gl-js),
  [proj4js](https://github.com/proj4js/proj4js), [geotiff.js](https://github.com/geotiffjs/geotiff.js),
  [pbf](https://github.com/mapbox/pbf), [vector-tile-js](https://github.com/mapbox/vector-tile-js),
  [vt-pbf](https://github.com/maplibre/vt-pbf), [togeojson](https://github.com/placemark/togeojson), [shpjs](https://github.com/calvinmetcalf/shapefile-js),
  [mgrs](https://github.com/proj4js/mgrs), [JSZip](https://github.com/Stuk/jszip) and
  [gifenc](https://github.com/mattdesl/gifenc) (self-hosted in `lib/`; versions and licences in the
  [SBOM](#libraries-sbom)).
- Highlight texts after [watson.ch](https://www.watson.ch/schweiz/klima/773592776-dieser-satellitenbilder-vergleich-zeigt-trockenheit-in-der-schweiz)
  (Philipp Reich, 10 August 2026) and [SRF Meteo](https://www.srf.ch/meteo/meteo-stories/trockenheit-in-der-schweiz-die-duerre-aus-der-vogelperspektive)
  (Roman Brogli, Timothy Schwitter, 9 July 2026) and [Blick](https://www.blick.ch/schweiz/ostschweiz/thurgau/untersee-faellt-auf-tiefsten-august-wert-seit-1930/49bvg7s)
  (12 August 2026), shortened and translated; the images are swissEO S2-SR TCI.
- Please note that AI (Claude Code with the Opus 5.5 model, medium effort) was used extensively to prepare this website, adapting it from the Copernicus Browser. The indices were edited and tested manually in QGIS or with rasterio and GDAL. Not for operational use.
- The repository keeps the upstream MIT license ([LICENSE.md](LICENSE.md)).
