/* Generates ../../lib/, the self-hosted runtime libraries of swisseo-browser.html.
   Usage:  cd tools/vendor && npm ci && node vendor.mjs
   File names carry the version (lib/maplibre-gl-6.16.0.mjs), so the deployed files can be cached as
   immutable and an upgrade is always a visible rename: after a version bump, update the LIB_CDN map in
   swisseo-browser.html and the SBOM table in README.md (this script warns when they drift).
   The *.esm.js bundles of the stubs are built with esbuild because the jsDelivr /+esm bundles the page used
   before are not self-contained (they import further jsDelivr URLs). */
import { build } from "esbuild";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..", "..");
const lib = path.join(root, "lib");
const mod = p => path.join(here, "node_modules", p);
const meta = pkg => JSON.parse(fs.readFileSync(mod(path.join(pkg, "package.json")), "utf8"));
const V = pkg => meta(pkg).version;

/* The dist files copied as they are (UMD / classic / self-contained ESM / CSS). */
const copies = [
  ["i18next",     "dist/umd/i18next.min.js",     v => `i18next-${v}.min.js`],
  ["maplibre-gl", "dist/maplibre-gl.css",        v => `maplibre-gl-${v}.css`],
  ["maplibre-gl", "dist/maplibre-gl.mjs",        v => `maplibre-gl-${v}.mjs`],
  ["maplibre-gl", "dist/maplibre-gl-worker.mjs", v => `maplibre-gl-worker-${v}.mjs`],
  ["proj4",       "dist/proj4.js",               v => `proj4-${v}.js`],
  ["geotiff",     "dist-browser/geotiff.js",     v => `geotiff-${v}.js`],
  ["gifenc",      "dist/gifenc.esm.js",          v => `gifenc-${v}.esm.js`],
  ["@tmcw/togeojson", "dist/togeojson.umd.js",   v => `togeojson-${v}.umd.js`],
  ["jszip",       "dist/jszip.min.js",           v => `jszip-${v}.min.js`],
  ["shpjs",       "dist/shp.min.js",             v => `shp-${v}.min.js`],
  ["mgrs",        "dist/mgrs.js",                v => `mgrs-${v}.js`],
  // Draco decoder of three.js (Apache-2.0) for the 3D objects: the WebAssembly build with its wrapper, and the JavaScript
  // build for a Content-Security-Policy without 'wasm-unsafe-eval' (the page picks one, loadThree)
  ["three",       "examples/jsm/libs/draco/gltf/draco_wasm_wrapper.js", v => `draco-wasm-wrapper-three-${v}.js`],
  ["three",       "examples/jsm/libs/draco/gltf/draco_decoder.wasm", v => `draco-decoder-three-${v}.wasm`],
  ["three",       "examples/jsm/libs/draco/gltf/draco_decoder.js", v => `draco-decoder-three-${v}.js`]
];

/* The ESM bundles (for MapLibre's workers; three.js for the 3D objects) and their self-test: the named exports the page
   imports. */
const bundles = [
  ["proj4",               "stubs/proj4.js",       v => `proj4-${v}.esm.js`,       m => typeof m.default === "function"],
  ["pbf",                 "stubs/pbf.js",         v => `pbf-${v}.esm.js`,         m => typeof m.PbfReader === "function"],
  ["@mapbox/vector-tile", "stubs/vector-tile.js", v => `vector-tile-${v}.esm.js`, m => typeof m.VectorTile === "function"],
  ["@maplibre/vt-pbf",    "stubs/vt-pbf.js",      v => `vt-pbf-${v}.esm.js`,      m => typeof m.fromVectorTileJs === "function"],
  ["three",               "stubs/three-tiles.js", v => `three-tiles-${v}.esm.js`, m => ["WebGLRenderer", "InstancedMesh", "ShadowMaterial",
                           "TextureLoader", "GLTFLoader", "DRACOLoader"].every(k => typeof m[k] === "function")]
];

/* Pinned raw files (immutable commit URLs). */
const FDC_SRC = "https://raw.githubusercontent.com/sentinel-hub/custom-scripts/" +
  "0a071cfc15adc91ae79cdda1cec6332133bb7565/sentinel-2/forest_disturbance_classification/script.js";
const downloads = [
  ["external-providers-3e5a2900.json",
   "https://raw.githubusercontent.com/geoadmin/web-mapviewer/3e5a2900/packages/mapviewer/src/" +
   "modules/menu/components/advancedTools/ImportCatalogue/external-providers.json",
   "WMS / WMTS provider list of geoadmin/web-mapviewer (BSD-3-Clause)"]
];

/* The Forest Disturbance Classification model is converted once into a static ES module: the page then
   imports the decision trees instead of compiling them with new Function(), so the production site needs
   no 'unsafe-eval' in its Content-Security-Policy. The checks are the ones the page used to run at
   runtime: the extracted code must consist of tree functions and arithmetic alone. */
function vendorFdc(src) {
  const a = src.indexOf("function pt0("), b = src.indexOf("function predict(");
  if (a < 0 || b < a) throw new Error("forest disturbance: unexpected format of the script");
  const code = src.slice(a, b);
  const rest = code.replace(/function pt\d+\(B02, B05, B06, B8A, B11, B12\)|return|\b(B02|B05|B06|B8A|B11|B12)\b/g, "");
  if (/[^\s\d.eE+\-<=?:(){};,]/.test(rest)) throw new Error("forest disturbance: the script contains unexpected code");
  const n = (code.match(/function pt\d+\(/g) || []).length;
  if (n < 100) throw new Error("forest disturbance: only " + n + " trees found");
  return ["/* Forest Disturbance Classification (Joanneum Research, EvoLand), CC BY-SA 4.0.",
    " * " + n + " decision trees, extracted by tools/vendor from",
    " * " + FDC_SRC,
    " * The page imports this module; it compiles no code at runtime. */",
    code.trimEnd(), "",
    "export const trees = [" + Array.from({ length: n }, (_, i) => "pt" + i).join(",") + "];", ""].join("\n");
}

fs.rmSync(lib, { recursive: true, force: true });
fs.mkdirSync(lib);

const made = [];
for (const [pkg, from, name] of copies) {
  const f = name(V(pkg));
  fs.copyFileSync(mod(path.join(pkg, from)), path.join(lib, f));
  made.push([f, pkg, V(pkg), meta(pkg).license]);
  console.log("copied  " + f);
}

/* geotiff.js decodes COG tiles in Web Workers with its own decoder worker, which the package ships only as a string
   (dist-module/worker/decoder.js, and inlined in the browser bundle, from where it would be started from a blob URL).
   It is written out as a classic script, so the page starts the worker from lib/ like any other file. */
{
  const src = fs.readFileSync(mod("geotiff/dist-module/worker/decoder.js"), "utf8");
  const m = /const source = ("(?:[^"\\]|\\.)*");/.exec(src);
  if (!m) throw new Error("geotiff: the decoder worker source was not found in dist-module/worker/decoder.js");
  const f = `geotiff-decoder-worker-${V("geotiff")}.js`;
  fs.writeFileSync(path.join(lib, f), `/* geotiff@${V("geotiff")} (${meta("geotiff").license}), its decoder worker, extracted by tools/vendor */\n` +
                   JSON.parse(m[1]) + "\n");
  made.push([f, "geotiff (decoder worker)", V("geotiff"), meta("geotiff").license]);
  console.log("extracted " + f);
}

for (const [pkg, stub, name] of bundles) {
  const f = name(V(pkg));
  await build({
    entryPoints: [path.join(here, stub)], bundle: true, format: "esm", platform: "browser",
    target: "es2020", minify: true, legalComments: "inline",
    banner: { js: `/* ${pkg}@${V(pkg)} (${meta(pkg).license}), bundled from npm by tools/vendor */` },
    outfile: path.join(lib, f), logLevel: "silent"
  });
  made.push([f, pkg, V(pkg), meta(pkg).license]);
  console.log("bundled " + f);
}

for (const [f, url, note] of downloads) {
  const r = await fetch(url);
  if (!r.ok) throw new Error("HTTP " + r.status + " for " + url);
  fs.writeFileSync(path.join(lib, f), Buffer.from(await r.arrayBuffer()));
  made.push([f, note, "", ""]);
  console.log("fetched " + f);
}

{
  const r = await fetch(FDC_SRC);
  if (!r.ok) throw new Error("HTTP " + r.status + " for " + FDC_SRC);
  const f = "forest-disturbance-trees-0a071cf.mjs";
  fs.writeFileSync(path.join(lib, f), vendorFdc(await r.text()));
  made.push([f, "Forest Disturbance Classification trees (Joanneum Research, EvoLand), " +
                "sentinel-hub/custom-scripts, CC BY-SA 4.0", "", ""]);
  console.log("converted " + f);
}

/* Self-test: the ESM files must load and export what swisseo-browser.html imports. */
for (const [pkg, , name, check] of bundles) {
  const m = await import(pathToFileURL(path.join(lib, name(V(pkg)))).href);
  if (!check(m)) throw new Error(name(V(pkg)) + ": expected export missing");
}
{
  const m = await import(pathToFileURL(path.join(lib, `gifenc-${V("gifenc")}.esm.js`)).href);
  for (const k of ["GIFEncoder", "quantize", "applyPalette"])
    if (typeof m[k] !== "function") throw new Error("gifenc: export " + k + " missing");
}
{
  const { trees } = await import(pathToFileURL(path.join(lib, "forest-disturbance-trees-0a071cf.mjs")).href);
  if (!Array.isArray(trees) || trees.length < 100 || typeof trees[0] !== "function")
    throw new Error("forest disturbance: the converted module does not export the trees");
  if (!Number.isFinite(trees[0](1200, 1500, 1800, 3000, 2200, 1500)))
    throw new Error("forest disturbance: a tree did not return a number");
  console.log("forest disturbance: " + trees.length + " trees");
}
{
  /* i18next is a classic UMD script in the page (it must also load from disk): run it the way a
     browser would, without module scope, and check it sets up a usable global */
  const src = fs.readFileSync(path.join(lib, `i18next-${V("i18next")}.min.js`), "utf8");
  const g = {};
  new Function("window", "self", "globalThis", src)(g, g, g);
  const i18next = g.i18next;
  if (!i18next || typeof i18next.init !== "function" || typeof i18next.t !== "function")
    throw new Error("i18next: the UMD build does not expose i18next.init / i18next.t");
  await i18next.init({ lng: "de", fallbackLng: "en", resources: {
    en: { app: { a: "Layer", n_one: "{{count}} layer", n_other: "{{count}} layers" } },
    de: { app: { a: "Ebene", n_one: "{{count}} Ebene", n_other: "{{count}} Ebenen" } } }, defaultNS: "app" });
  if (i18next.t("a") !== "Ebene" || i18next.t("n", { count: 2 }) !== "2 Ebenen" ||
      i18next.t("missing", { defaultValue: "English" }) !== "English")
    throw new Error("i18next: translation, plurals or defaultValue do not work");
  console.log("i18next: translation, plurals and fallback OK");
}
{
  /* the decoder worker, run in a stand-in worker scope: a DEFLATE tile with a horizontal predictor (as the swissEO
     bands) must come back decoded */
  const { deflateSync } = await import("node:zlib");
  const src = fs.readFileSync(path.join(lib, `geotiff-decoder-worker-${V("geotiff")}.js`), "utf8");
  const scope = { listeners: [], addEventListener(t, f) { if (t === "message") this.listeners.push(f); } };
  const answer = new Promise(res => { scope.postMessage = d => res(d); });
  new Function("self", "globalThis", src)(scope, scope);
  if (!scope.listeners.length) throw new Error("geotiff decoder worker: no message listener");
  const W = 4, H = 2, v = new Uint16Array([10, 20, 30, 40, 5, 5, 5, 5]), diff = new Uint16Array(v);
  for (let y = 0; y < H; y++) for (let x = W - 1; x > 0; x--) diff[y * W + x] = v[y * W + x] - v[y * W + x - 1];
  const buf = deflateSync(Buffer.from(diff.buffer));
  scope.listeners.forEach(f => f({ data: { id: 7, buffer: buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.length),
    fileDirectory: { Compression: 8, Predictor: 2, TileWidth: W, TileLength: H, BitsPerSample: [16], PlanarConfiguration: 1 } } }));
  const out = await Promise.race([answer, new Promise((_, rej) => setTimeout(() => rej(new Error("geotiff decoder worker: no answer")), 5000))]);
  if (out.id !== 7 || new Uint16Array(out.decoded).join() !== v.join()) throw new Error("geotiff decoder worker: wrong result");
  console.log("geotiff decoder worker: DEFLATE with predictor OK");
}
{
  /* both Draco decoders must start: the WebAssembly one with the .wasm file as it is served */
  const V3 = V("three"), read = f => fs.readFileSync(path.join(lib, f));
  for (const [f, wasm] of [[`draco-wasm-wrapper-three-${V3}.js`, `draco-decoder-three-${V3}.wasm`], [`draco-decoder-three-${V3}.js`, null]]) {
    // as a browser worker sees it: no module system, no process
    const make = new Function("module", "exports", "process", read(f).toString("utf8") + ";return DracoDecoderModule;")();
    const d = await Promise.race([new Promise(res => make({ ...(wasm ? { wasmBinary: new Uint8Array(read(wasm)).buffer } : {}), onModuleLoaded: res })),
      new Promise((_, rej) => setTimeout(() => rej(new Error(f + ": the Draco decoder did not start")), 10000))]);
    if (typeof d.Decoder !== "function") throw new Error(f + ": no Decoder");
  }
  console.log("Draco decoders: WebAssembly and JavaScript start");
}
console.log("self-test OK");

fs.writeFileSync(path.join(lib, "README.md"), [
  "# lib/ (generated)", "",
  "Generated by `tools/vendor` (`npm ci && node vendor.mjs`); do not edit by hand.",
  "These are the runtime libraries of `swisseo-browser.html`, self-hosted so that no third-party CDN",
  "runs code on the site (the pinned CDN URLs remain only as the fallback when the page is opened as a",
  "local file). Versions are pinned in `tools/vendor/package.json`; licences are listed in the SBOM",
  "table of the repository README.", "",
  ...made.map(([f, src, v]) => `- \`${f}\`: ${src}${v ? " " + v : ""}`), ""
].join("\n"));

/* Warn when the page and lib/ drift apart. The page names a library either as a path in a tag
   (href="lib/x.css") or as a key of its LIB_CDN map (libUrl("x.js")), so both are matched by name. */
const page = fs.readFileSync(path.join(root, "swisseo-browser.html"), "utf8");
const refs = new Set([...page.matchAll(/"lib\/([^"]+)"|libUrl\("([^"]+)"\)|^\s*"([^"]+)":\s*"https:/gm)]
  .map(m => m[1] || m[2] || m[3]));
for (const r of refs) if (!made.some(([f]) => f === r))
  console.warn("WARNING: the page asks for lib/" + r + ", which was not generated");
for (const [n] of made) if (!refs.has(n))
  console.warn("WARNING: lib/" + n + " is not used by the page");
console.log("lib/ complete: " + made.length + " files");
