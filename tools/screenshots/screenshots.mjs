/* The screenshots of the help page, in every language.

     cd tools/screenshots && npm ci && npx playwright install chromium
     node screenshots.mjs                          all views, all languages
     node screenshots.mjs --lang de,fr --only overview,calendar

   English goes to docs/img/<name>.jpg, the other languages to docs/img/<lng>/<name>.jpg (the help page
   falls back to English for a picture that is missing). The repository is served on a local port,
   because the translations are fetched over http; the page is shown as production shows it (no
   integration bar). Every view is a permalink plus the few clicks a link cannot express, in a window of
   1400 x 900 px; a crop takes a part of the window or one dialog. The data are those of 13 August 2026:
   a view whose data change (a new mosaic version) may need its date or place adjusted here. */
import { createServer } from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const arg = name => { const i = process.argv.indexOf("--" + name); return i > 0 ? process.argv[i + 1] : null; };
const LANGS = (arg("lang") || "en,de,fr,it").split(",");
const ONLY = arg("only") ? arg("only").split(",") : null;
const DATE = "2026-08-13";

const MIME = { ".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript", ".css": "text/css",
  ".json": "application/json", ".geojson": "application/geo+json", ".png": "image/png", ".jpg": "image/jpeg", ".md": "text/markdown" };
// the custom mask of its figure: two polygons near Kerzers (WGS84), served next to the page
const MASK = { type: "FeatureCollection", features: [
  [[7.170, 46.972], [7.190, 46.972], [7.190, 46.985], [7.170, 46.985], [7.170, 46.972]],
  [[7.205, 46.960], [7.228, 46.958], [7.232, 46.973], [7.210, 46.976], [7.205, 46.960]]
].map(r => ({ type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [r] } })) };
const srv = createServer((req, res) => {
  const p = decodeURIComponent(new URL(req.url, "http://x").pathname);
  if (p === "/__shots/mask.geojson") { res.writeHead(200, { "content-type": MIME[".geojson"] }); res.end(JSON.stringify(MASK)); return; }
  let f = path.join(ROOT, p);
  if (!f.startsWith(ROOT)) { res.writeHead(403); res.end(); return; }
  if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, "index.html");
  if (!fs.existsSync(f)) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { "content-type": MIME[path.extname(f)] || "application/octet-stream" });
  res.end(fs.readFileSync(f));
});
const port = await new Promise(r => srv.listen(0, () => r(srv.address().port)));
const BASE = `http://localhost:${port}/swisseo-browser.html`;

/* an area of interest in the link: a rectangle in LV95 */
const b64 = o => Buffer.from(JSON.stringify(o)).toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
const box = (x0, y0, x1, y1) => b64({ type: "Polygon", coordinates: [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]] });
const SEELAND = box(2577000, 1203000, 2588000, 1213000);          // 110 km²
const ALETSCH = { center: "2644500,1141000", zoom: 19.2, "3d": "true", pitch: 62, bearing: 0, labels: "true" };
const link = (o, lng) => {
  const p = new URLSearchParams(Object.assign({ fromTime: DATE + "T00:00:00.000Z", toTime: DATE + "T23:59:59.999Z",
    themeId: "DEFAULT", layerId: "true" }, o));
  if (lng !== "en") p.set("lang", lng);
  return BASE + "?" + p.toString();
};

/* the views: link parameters, what to do once the page is ready, and what to keep */
const VIEWS = {
  "overview":        { q: { center: "2622000,1180000", zoom: 17.6 } },
  "place-search":    { q: { center: "2612000,1186000", zoom: 18.6 }, clip: [400, 0, 1000, 420],
                       act: async p => { await p.fill("#psIn", "Thun"); await p.waitForTimeout(2500); } },
  "calendar":        { q: { center: "2612000,1186000", zoom: 18.6 }, clip: [0, 0, 760, 560],
                       act: async p => { await p.click("#btnCal"); await p.waitForTimeout(3000); } },
  "layer-menu":      { q: { center: "2582000,1208000", zoom: 19, layerId: "ndvi", layerMenu: "open" } },
  "mask-lnf":        { q: { center: "2579500,1200500", zoom: 20.5, layerId: "ndvi", layerMenu: "open", vegetationMask: "lnf:a.dw.dp" },
                       scroll: "#layerlist .vrow", wait: 20000 },
  "pixel-inspector": { q: { center: "2579500,1200500", zoom: 21, layerId: "ndvi" },
                       act: async p => { await p.click("#btnInspect"); await p.mouse.click(900, 470); await p.waitForTimeout(15000); } },
  "statistics":      { q: { center: "2582500,1208000", zoom: 18.6, layerId: "ndvi", aoi: SEELAND },
                       act: async p => { await p.click("#aoiStats"); await p.waitForTimeout(60000); } },
  "terrain-3d":      { q: ALETSCH, wait: 20000 },
  "forest-vhi":      { q: { center: "2573500,1214500", zoom: 20, themeId: "FOREST", layerId: "vhidef", layerMenu: "open" }, wait: 60000 },
  "effects":         { q: { center: "2612000,1186000", zoom: 18.6, layerMenu: "open" }, clip: [0, 0, 420, 900],
                       act: async p => { await p.evaluate(() => { const b = [...document.querySelectorAll("#layerlist .lyr-body > button.lnk")].find(x => x.style.marginTop === "14px"); if (b) b.click(); });
                                         await p.waitForTimeout(1500); }, scroll: "#layerlist .lyr-body > button.lnk[style*='14px']" },
  "mask-lfi":        { q: { center: "2683500,1235500", zoom: 20.3, layerId: "ndvi", layerMenu: "open", vegetationMask: "lfi-mixed:30.85:m3" },
                       scroll: "#layerlist .vrow", wait: 20000 },
  "mask-eth":        { q: { center: "2683500,1235500", zoom: 20.3, layerId: "ndvi", layerMenu: "open", vegetationMask: "eth-sp:1.2.3.4.5.6" },
                       scroll: "#layerlist .vrow", wait: 20000 },
  "custom-mask":     { q: { center: "2581000,1200500", zoom: 20, layerId: "ndvi", layerMenu: "open", customMask: "in",
                            maskUrl: `http://localhost:${port}/__shots/mask.geojson` },
                       scroll: "#layerlist .cmrow", wait: 15000 },
  "compare":         { q: { center: "2644500,1141000", zoom: 19.4, compareMode: "split",
                            compareLayers: b64([{ l: "true", d: "2019-08-18", c: 100, s: {}, v: [2644500, 1141000, 19.4] },
                                                { l: "true", d: DATE, c: 100, s: {}, v: [2644500, 1141000, 19.4] }]),
                            comparedOpacity: "[1,1]", comparedClipping: "[[0,0.5],[0,1]]" },
                       act: async p => { await p.click("#dcCompare"); await p.waitForTimeout(8000); } },
  "highlights":      { q: { center: "2660000,1170000", zoom: 17, themeId: "DROUGHT2026" },
                       act: async p => { await p.click("#layerlist .hl"); await p.waitForTimeout(15000);
                                         await p.click("#dcLayers"); await p.waitForTimeout(1500);
                                         await p.click("#layerlist .hl.on .ex"); await p.waitForTimeout(1500); } },
  "wms":             { q: { center: "2660000,1190000", zoom: 15.6, panel: "wms", wmsUrl: "https://wms.geo.admin.ch/",
                            wmsLayer: "ch.bafu.bundesinventare-bln" }, wait: 15000 },
  "3d-settings":     { q: ALETSCH, act: async p => { await p.click("#btn3dSet"); await p.waitForTimeout(1500); }, wait: 20000 },
  "sun-time":        { q: ALETSCH, wait: 20000,
                       act: async p => { await p.click("#btnSun"); await p.waitForTimeout(800);
                                         await p.fill("#sunClock", "16:45"); await p.dispatchEvent("#sunClock", "change");
                                         await p.waitForTimeout(8000); } },
  "import":          { q: { center: "2612000,1186000", zoom: 18.6 }, el: "#aoiModal .box",
                       act: async p => { await p.click("#btnAoi"); await p.waitForTimeout(500); await p.click("#aoiUpload"); await p.waitForTimeout(1000); } },
  "image-download":  { q: { center: "2582000,1208000", zoom: 19, layerId: "ndvi" }, el: "#expModal .box",
                       act: async p => { await p.click("#btnExport"); await p.waitForTimeout(800);
                                         await p.click('#expTabs [data-e="analytical"]'); await p.waitForTimeout(1200); } },
  "timelapse":       { q: { center: "2581000,1205000", zoom: 20, aoi: box(2578000, 1202000, 2584000, 1208000) },
                       act: async p => { await p.click("#btnTimelapse"); await p.waitForTimeout(1000);
                                         await p.fill("#tlFrom", "2026-04-01"); await p.fill("#tlTo", "2026-09-30");
                                         await p.selectOption("#tlPer", "month"); await p.click("#tlSearch");
                                         await p.waitForTimeout(90000);
                                         await p.click("#tlPreview"); await p.waitForTimeout(60000); } },
  "feedback":        { q: { center: "2612000,1186000", zoom: 18.6 }, clip: [0, 0, 420, 700],
                       act: async p => { await p.click('[data-t="info"]'); await p.waitForTimeout(1500); } }
};

/* scrolls the menu so that an element stands in its upper third */
async function scrollTo(p, sel) {
  await p.evaluate(s => {
    const e = document.querySelector(s), v = document.querySelector("#p-vis");
    if (e && v) v.scrollTop += e.getBoundingClientRect().top - v.getBoundingClientRect().top - v.clientHeight / 6;
  }, sel);
  await p.waitForTimeout(800);
}
/* ready: the loading indicator has been hidden for two seconds (at most 90 s) */
async function idle(p, extra) {
  const t0 = Date.now();
  let quiet = 0;
  while (Date.now() - t0 < 90000 && quiet < 4) {
    await p.waitForTimeout(500);
    quiet = await p.evaluate(() => document.querySelector("#loading").hidden) ? quiet + 1 : 0;
  }
  if (extra) await p.waitForTimeout(extra);
}

const browser = await chromium.launch({ channel: "chromium", args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
let failed = 0;
for (const lng of LANGS) {
  const dir = lng === "en" ? path.join(ROOT, "docs/img") : path.join(ROOT, "docs/img", lng);
  fs.mkdirSync(dir, { recursive: true });
  for (const [name, v] of Object.entries(VIEWS)) {
    if (ONLY && !ONLY.includes(name)) continue;
    const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 }, locale: { en: "en-GB", de: "de-CH", fr: "fr-CH", it: "it-CH" }[lng] });
    const p = await ctx.newPage();
    const errors = [];
    p.on("pageerror", e => errors.push(String(e)));
    try {
      await p.goto(link(v.q, lng), { waitUntil: "load", timeout: 90000 });
      await p.waitForSelector(".maplibregl-canvas", { timeout: 60000 });
      // as production shows it: without the integration bar
      await p.evaluate(() => { document.documentElement.dataset.env = "prod"; window.dispatchEvent(new Event("resize")); });
      await idle(p, v.wait || 4000);
      if (v.act) { await v.act(p); await idle(p, 1500); }
      if (v.scroll) await scrollTo(p, v.scroll);
      const file = path.join(dir, name + ".jpg"), opt = { path: file, type: "jpeg", quality: 84 };
      if (v.el) await p.locator(v.el).screenshot(opt);
      else await p.screenshot(Object.assign(opt, v.clip ? { clip: { x: v.clip[0], y: v.clip[1], width: v.clip[2], height: v.clip[3] } } : {}));
      console.log(lng + " " + name + (errors.length ? "  (page error: " + errors[0].slice(0, 120) + ")" : ""));
    } catch (e) {
      failed++;
      console.log(lng + " " + name + "  FAILED: " + String(e.message || e).split("\n")[0]);
    }
    await ctx.close();
  }
}
await browser.close();
srv.close();
if (failed) { console.log(failed + " views failed"); process.exit(1); }
