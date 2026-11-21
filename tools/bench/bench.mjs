/* Map performance benchmark: how fast the tiles of the 2D map load and render while panning and zooming.

     cd tools/bench && npm ci && npx playwright install chromium
     node bench.mjs                                   True color and NDVI, every scenario, once
     node bench.mjs --layers ndvi --runs 3            the median of three runs
     node bench.mjs --out after.json --compare baseline.json
     node bench.mjs --throttle                        a 20 Mbit/s, 40 ms connection (Chrome's network emulation)
     node bench.mjs --heap 20                         JS heap after 20 date changes
     node bench.mjs --gpu --headed                    the machine's graphics card instead of software WebGL

   The repository is served on a local port and swisseo-browser.html is instrumented on the way (the files are not
   changed): the swisseo:// tile handler is wrapped, fetch() is counted, decoded COG tiles are counted, long tasks
   and a CPU profile of the main thread are recorded. Per scenario it reports the data and basemap tiles the map
   asked for, when the first, the middle and the last data tile were ready (ms after the interaction), aborted tiles
   and the work they still did, tiles delivered after they had left the view, COG requests and MB, re-fetched byte
   ranges, decodes (and repeated decodes of a tile already decoded once), and the main thread's long tasks.
   Same view, date and window every time (Seeland, 13 August 2026, 1400 x 900 px), so runs can be compared. */
import { createServer } from "node:http";
import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const arg = (name, dflt) => { const i = process.argv.indexOf("--" + name); return i < 0 ? dflt : (process.argv[i + 1] && !process.argv[i + 1].startsWith("--") ? process.argv[i + 1] : true); };
const LAYERS = String(arg("layers", "true,ndvi")).split(",");
const RUNS = +arg("runs", 1);
const ONLY = arg("scenarios", null) ? String(arg("scenarios")).split(",") : null;
const HEAP = arg("heap", null) === null ? 0 : arg("heap") === true ? 20 : +arg("heap");
const THROTTLE = !!arg("throttle", false), GPU = !!arg("gpu", false), HEADED = !!arg("headed", false);
const OUT = arg("out", null), CMP = arg("compare", null);
const VIEW = "zoom=19.5&center=2582000,1208000&fromTime=2026-08-13T00%3A00%3A00.000Z&toTime=2026-08-13T23%3A59%3A59.999Z&themeId=DEFAULT";

/* ---- the instrumentation, added to the served page ---- */
const HOOKS = [
  ['maplibregl.addProtocol("swisseo", async (params, ctrl) => {', 'maplibregl.addProtocol("swisseo", window.__wrapProto(async (params, ctrl) => {'],
  [/(\n {2}\} finally \{[^\n]*lyr\.pending--; pendingSoon\(\); \}\n)\}\);/, "$1}));"],     // the end of that handler
  ["const setCursor = c =>", "window.__map = map; window.__viewBox = () => viewBox();\nconst setCursor = c =>"],
  ["const pyrCache = new Map();", "const pyrCache = new Map(); window.__countDecodes && window.__countDecodes(GeoTIFF);"]
];
/* --define NAME=value (repeatable): the page's `const NAME = <number>` takes another value, to compare settings such as
   TILE_TURNS or DATA_MAXZOOM without editing the page */
const DEFINES = process.argv.flatMap((a, i) => a === "--define" ? [process.argv[i + 1].split("=")] : []);
function instrument(html) {
  for (const [name, val] of DEFINES) {
    const re = new RegExp("(const " + name + " = )[\\d.]+");
    if (!re.test(html)) throw new Error("bench: --define " + name + ": no `const " + name + " = <number>` in the page");
    html = html.replace(re, "$1" + val);
  }
  for (const [a, b] of HOOKS) {
    if (typeof a === "string" ? !html.includes(a) : !a.test(html))
      throw new Error("bench: the page no longer contains " + String(a).slice(0, 70) + ": update HOOKS");
    html = html.replace(a, b);
  }
  return html;
}
const MIME = { ".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript", ".css": "text/css",
  ".json": "application/json", ".png": "image/png", ".jpg": "image/jpeg", ".svg": "image/svg+xml" };
const srv = createServer((req, res) => {
  const f = path.join(ROOT, decodeURIComponent(new URL(req.url, "http://x").pathname));
  if (!f.startsWith(ROOT) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); res.end(); return; }
  let body = fs.readFileSync(f);
  if (path.basename(f) === "swisseo-browser.html") body = instrument(body.toString("utf8"));
  res.writeHead(200, { "content-type": MIME[path.extname(f)] || "application/octet-stream" });
  res.end(body);
});
const port = await new Promise(r => srv.listen(0, () => r(srv.address().port)));

/* runs in the page before its own scripts */
const INIT = () => {
  const B = window.__bench = { phase: "load", t0: { load: performance.now() }, tiles: [], reqs: [], long: [], jpeg: {}, dec: {} };
  const meet = (a, b) => a[0] < b[2] && a[2] > b[0] && a[1] < b[3] && a[3] > b[1];
  // still wanted: in the view and at the tile zoom MapLibre uses for it (rounded zoom, at most the source's maxzoom)
  const inView = (z, x, y, maxz) => {
    try {
      const span = 512 * 2560 / 2 ** z, b = [2420000 + x * span, 1350000 - (y + 1) * span, 2420000 + (x + 1) * span, 1350000 - y * span];
      return meet(b, window.__viewBox()) && z === Math.min(maxz, Math.round(window.__map.getZoom()));
    } catch (e) { return null; }
  };
  window.__wrapProto = fn => async (params, ctrl) => {
    const m = /^swisseo:\/\/(\w+)\/(\d+)\/(\d+)\/(\d+)/.exec(params.url), z = +m[2], x = +m[3], y = +m[4];
    const t = { url: params.url, z, phase: B.phase, t0: performance.now(), end: null, abortedAt: null, out: "", inView: null };
    B.tiles.push(t);
    ctrl.signal.addEventListener("abort", () => { t.abortedAt = performance.now(); });
    try {
      const r = await fn(params, ctrl);
      t.out = r && r.data ? "img" : "none";
      const src = window.__map.getSource(m[1]);
      t.inView = inView(z, x, y, src && src.maxzoom != null ? src.maxzoom : 14);
      return r;
    } catch (e) { t.out = (e && e.name) || "err"; throw e; }
    finally { t.end = performance.now(); }
  };
  // decoded COG tiles (geotiff.js decoders: DEFLATE bands and masks; the TCI's JPEG is counted as jpegDecodes): a tile
  // is told apart by its image and a hash of its compressed bytes, so a tile decoded a second time counts as "again"
  window.__countDecodes = G => {
    const P = G.BaseDecoder.prototype, dec = P.decode, ids = new WeakMap(), seen = new Set();
    let nid = 0;
    P.decode = function (fd, buffer) {
      if (!ids.has(fd)) ids.set(fd, ++nid);
      let h = buffer.byteLength;
      const u = new Uint8Array(buffer, 0, Math.min(256, buffer.byteLength));
      for (let i = 0; i < u.length; i++) h = (h * 31 + u[i]) | 0;
      const k = ids.get(fd) + "/" + h, d = B.dec[B.phase] || (B.dec[B.phase] = { n: 0, again: 0 });
      d.n++; if (seen.has(k)) d.again++; seen.add(k);
      return dec.call(this, fd, buffer);
    };
  };
  const f0 = window.fetch.bind(window);
  window.fetch = async (input, init = {}) => {
    const url = typeof input === "string" ? input : input.url, h = init.headers || {};
    const r = { url, range: h.Range || h.range || (h.get ? h.get("Range") : "") || "", phase: B.phase, t0: performance.now(), end: null, bytes: 0, st: "" };
    B.reqs.push(r);
    try {
      const res = await f0(input, init);
      for (const k of ["arrayBuffer", "json", "text", "blob"]) {
        const o = res[k].bind(res);
        res[k] = async () => {
          try { const b = await o(); if (b && b.byteLength != null) r.bytes = b.byteLength; else if (b && b.size != null) r.bytes = b.size; r.st = "ok"; return b; }
          catch (e) { r.st = e.name; throw e; } finally { r.end = performance.now(); }
        };
      }
      if (!res.ok) { r.st = "http" + res.status; r.end = performance.now(); }
      return res;
    } catch (e) { r.st = e.name; r.end = performance.now(); throw e; }
  };
  const cib = window.createImageBitmap.bind(window);
  window.createImageBitmap = (src, ...a) => { if (src instanceof Blob) B.jpeg[B.phase] = (B.jpeg[B.phase] || 0) + 1; return cib(src, ...a); };
  try { new PerformanceObserver(l => l.getEntries().forEach(e => B.long.push({ d: e.duration, phase: B.phase }))).observe({ type: "longtask", buffered: true }); } catch (e) {}
  window.__stats = phase => {
    const t0 = B.t0[phase], tiles = B.tiles.filter(t => t.phase === phase);
    const kind = arr => {
      const img = arr.filter(t => t.out === "img"), ab = arr.filter(t => t.abortedAt != null);
      const ends = img.map(t => t.end - t0).sort((a, b) => a - b);
      let c = 0, maxc = 0;
      arr.flatMap(t => [[t.t0, 1], [t.end || t.t0, -1]]).sort((a, b) => a[0] - b[0] || a[1] - b[1]).forEach(e => { c += e[1]; maxc = Math.max(maxc, c); });
      return { n: arr.length, img: img.length, aborted: arr.filter(t => t.out === "AbortError").length,
        workAfterAbort: Math.round(ab.reduce((a, t) => a + ((t.end || t.abortedAt) - t.abortedAt), 0)),
        outOfView: img.filter(t => t.inView === false).length,
        first: ends.length ? Math.round(ends[0]) : null, half: ends.length ? Math.round(ends[Math.floor(ends.length / 2)]) : null,
        last: ends.length ? Math.round(ends[ends.length - 1]) : null, concurrent: maxc,
        zooms: [...new Set(arr.map(t => t.z))].sort((a, b) => a - b).join(",") };
    };
    const i0 = B.reqs.findIndex(q => q.phase === phase), before = new Set(B.reqs.slice(0, i0 < 0 ? 0 : i0).map(r => r.url + "|" + r.range));
    const rq = B.reqs.filter(r => r.phase === phase), mine = new Set();
    let again = 0;
    rq.forEach(r => { const k = r.url + "|" + r.range; if (mine.has(k) || before.has(k)) again++; mine.add(k); });
    const lt = B.long.filter(e => e.phase === phase), dec = B.dec[phase] || { n: 0, again: 0 };
    return { data: kind(tiles.filter(t => !/[?&]L=/.test(t.url))), base: kind(tiles.filter(t => /[?&]L=/.test(t.url))),
      cogRequests: rq.filter(r => /\.tif/.test(r.url)).length, mb: +(rq.reduce((a, r) => a + r.bytes, 0) / 1e6).toFixed(2),
      refetched: again, decodes: dec.n, decodedAgain: dec.again, jpegDecodes: B.jpeg[phase] || 0,
      longTasks: lt.length, longSum: Math.round(lt.reduce((a, e) => a + e.d, 0)), longMax: Math.round(Math.max(0, ...lt.map(e => e.d))),
      zoom: +window.__map.getZoom().toFixed(2) };
  };
};

/* ---- scenarios ---- */
async function settle(page, maxMs = 40000) {
  const t = Date.now();
  let quiet = 0;
  while (Date.now() - t < maxMs && quiet < 6) {
    await page.waitForTimeout(250);
    const busy = await page.evaluate(() => { const B = window.__bench, now = performance.now();
      return B.tiles.some(x => x.end == null) || B.reqs.some(x => x.end == null && now - x.t0 < 20000); });
    quiet = busy ? 0 : quiet + 1;
  }
  return Math.max(0, Date.now() - t - 1500);
}
const CX = 900, CY = 450;
const drag = async (p, dx, dy, steps = 12) => { await p.mouse.move(CX, CY); await p.mouse.down(); await p.mouse.move(CX - dx, CY - dy, { steps }); await p.mouse.up(); };
const zin = p => p.click(".zoom-ctl button:first-child"), zout = p => p.click(".zoom-ctl button:last-child");
const SCENARIOS = [
  ["smallPan", p => drag(p, 150, 0)],
  ["largePan", p => drag(p, 800, 300)],
  ["fastPan", async p => { for (let i = 0; i < 6; i++) { await drag(p, 350, 60, 5); await p.waitForTimeout(40); } }],
  ["longPan", async p => { for (let i = 0; i < 8; i++) { await drag(p, 700, i % 2 ? 100 : -100, 5); await p.waitForTimeout(30); } }],
  ["zoomIn", p => zin(p)],
  ["zoomIn2", p => zin(p)],
  ["zoomDeep", async p => { await zin(p); await p.waitForTimeout(400); await zin(p); }],
  ["zoomOut", p => zout(p)],
  ["rapidZoom", async p => { for (const f of [zin, zout, zin, zout, zin]) { await f(p); await p.waitForTimeout(150); } }],
  ["panAfterZoom", async p => { await zout(p); await p.waitForTimeout(200); await drag(p, 500, 0); }],
  ["zoomBack", async p => { for (let i = 0; i < 4; i++) { await zout(p); await p.waitForTimeout(350); } }]
].filter(([n]) => !ONLY || ONLY.includes(n));

async function benchLayer(browser, layer) {
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 } });
  await ctx.addInitScript(INIT);
  const page = await ctx.newPage(), cdp = await ctx.newCDPSession(page);
  if (THROTTLE) {
    await cdp.send("Network.enable");
    await cdp.send("Network.emulateNetworkConditions", { offline: false, latency: 40, downloadThroughput: 20e6 / 8, uploadThroughput: 5e6 / 8 });
  }
  await cdp.send("Profiler.enable");
  await cdp.send("Profiler.setSamplingInterval", { interval: 1000 });
  await cdp.send("Profiler.start");
  await page.goto("http://localhost:" + port + "/swisseo-browser.html?" + VIEW + "&layerId=" + layer);
  await page.waitForSelector(".maplibregl-canvas");
  const res = { load: Object.assign({ settle: await settle(page, 90000) }, await page.evaluate(() => window.__stats("load"))) };
  for (const [name, act] of SCENARIOS) {
    await page.evaluate(n => { window.__bench.phase = n; window.__bench.t0[n] = performance.now(); }, name);
    await act(page);
    res[name] = Object.assign({ settle: await settle(page) }, await page.evaluate(n => window.__stats(n), name));
  }
  if (HEAP) {
    await cdp.send("HeapProfiler.enable");
    const used = async () => { await cdp.send("HeapProfiler.collectGarbage"); return Math.round((await cdp.send("Runtime.getHeapUsage")).usedSize / 1e6); };
    const h0 = await used(), steps = [];
    for (let i = 0; i < HEAP; i++) {
      await page.evaluate(n => { window.__bench.phase = n; window.__bench.t0[n] = performance.now(); }, "date" + i);
      await page.click("#dPrev");
      await settle(page);
      if ((i + 1) % 5 === 0) steps.push(await used());
    }
    res.heap = { startMB: h0, everyFiveDatesMB: steps };
  }
  const { profile } = await cdp.send("Profiler.stop");
  const dt = {};
  profile.samples.forEach((id, i) => { dt[id] = (dt[id] || 0) + (profile.timeDeltas[i] || 0); });
  const fn = {}, file = {};
  profile.nodes.forEach(nd => {
    const s = (dt[nd.id] || 0) / 1000, cf = nd.callFrame;
    if (!s || /^\((idle|program)\)$/.test(cf.functionName)) return;
    const u = (cf.url || "").split("/").pop().split("?")[0] || "(native)", k = u + " " + (cf.functionName || "(anonymous)") + ":" + (cf.lineNumber + 1);
    fn[k] = (fn[k] || 0) + s; file[u] = (file[u] || 0) + s;
  });
  res.cpu = { byFile: Object.fromEntries(Object.entries(file).sort((a, b) => b[1] - a[1]).slice(0, 6).map(([k, v]) => [k, Math.round(v)])),
              top: Object.entries(fn).sort((a, b) => b[1] - a[1]).slice(0, 15).map(([k, v]) => Math.round(v) + " ms " + k) };
  res.renderer = await page.evaluate(() => { try { const gl = document.createElement("canvas").getContext("webgl2"), e = gl.getExtension("WEBGL_debug_renderer_info");
    return e ? gl.getParameter(e.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER); } catch (e) { return "?"; } });
  await ctx.close();
  return res;
}

/* median over runs, per number */
function median(rs) {
  if (rs.length === 1) return rs[0];
  const walk = vs => {
    if (typeof vs[0] === "number") { const s = vs.filter(v => v != null).sort((a, b) => a - b); return s.length ? s[Math.floor(s.length / 2)] : null; }
    if (vs[0] && typeof vs[0] === "object" && !Array.isArray(vs[0])) return Object.fromEntries(Object.keys(vs[0]).map(k => [k, walk(vs.map(v => v && v[k]))]));
    return vs[0];
  };
  return walk(rs);
}

const browser = await chromium.launch({ channel: "chromium", headless: !HEADED,
  args: GPU ? ["--enable-gpu", "--ignore-gpu-blocklist"] : ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
const results = {};
let renderer = "";
for (const layer of LAYERS) {
  const runs = [];
  for (let i = 0; i < RUNS; i++) runs.push(await benchLayer(browser, layer));
  renderer = runs[0].renderer;
  results[layer] = median(runs.map(r => { const c = Object.assign({}, r); delete c.renderer; return c; }));
}
await browser.close();
srv.close();

let commit = "";
try { commit = execSync("git rev-parse --short HEAD", { cwd: ROOT }).toString().trim() + (execSync("git status --porcelain swisseo-browser.html", { cwd: ROOT }).toString().trim() ? "+changes" : ""); } catch (e) {}
const report = { meta: { date: new Date().toISOString(), commit, runs: RUNS, throttle: THROTTLE, renderer, cpus: (await import("node:os")).cpus().length,
                         defines: Object.fromEntries(DEFINES) }, results };

/* ---- the table ---- */
const old = CMP ? JSON.parse(fs.readFileSync(path.resolve(CMP), "utf8")).results : null;
const v = x => x == null ? "-" : String(x);
const pair = (a, b) => b === undefined ? v(a) : v(b) + "→" + v(a);
console.log("commit " + commit + " · " + renderer + " · " + report.meta.cpus + " CPUs" + (THROTTLE ? " · 20 Mbit/s, 40 ms" : "") +
  (DEFINES.length ? " · " + DEFINES.map(d => d.join("=")).join(", ") : "") + (RUNS > 1 ? " · median of " + RUNS : "") + (CMP ? " · before→after against " + CMP : ""));
for (const [layer, r] of Object.entries(results)) {
  console.log("\n== " + layer);
  console.log(["scenario", "zoom", "data tiles", "first/half/last ms", "aborted (work ms)", "out of view", "basemap tiles", "COG req", "MB", "refetched", "decodes (again)", "long tasks sum/max ms"].join(" | "));
  for (const [ph, s] of Object.entries(r)) {
    if (!s || !s.data) continue;
    const o = old && old[layer] && old[layer][ph], g = (f) => o ? f(o) : undefined;
    console.log([ph, s.zoom, pair(s.data.n, g(x => x.data.n)),
      pair(s.data.first, g(x => x.data.first)) + " / " + pair(s.data.half, g(x => x.data.half)) + " / " + pair(s.data.last, g(x => x.data.last)),
      pair(s.data.aborted, g(x => x.data.aborted)) + " (" + s.data.workAfterAbort + ")", s.data.outOfView,
      pair(s.base.n, g(x => x.base.n)), pair(s.cogRequests, g(x => x.cogRequests)), pair(s.mb, g(x => x.mb)), s.refetched,
      pair(s.decodes, g(x => x.decodes)) + " (" + s.decodedAgain + ")",
      pair(s.longSum, g(x => x.longSum)) + " / " + pair(s.longMax, g(x => x.longMax))].join(" | "));
  }
  if (r.heap) console.log("heap MB: start " + r.heap.startMB + ", after every 5 dates " + r.heap.everyFiveDatesMB.join(", "));
  console.log("main thread ms by file: " + JSON.stringify(r.cpu.byFile));
  r.cpu.top.forEach(l => console.log("   " + l));
}
if (OUT) { fs.writeFileSync(path.resolve(OUT), JSON.stringify(report, null, 1) + "\n"); console.log("\nwritten " + OUT); }
