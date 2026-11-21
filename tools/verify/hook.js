// Appended to the page's module by tools/verify/serve.py: exposes the page's own functions to the verification
// (tools/verify/drive.py). serve.py fills in the getters and the ramp names below.
{
  const T = {
/*GETTERS*/
  };
  const RAMPS = /*RAMPS*/;
  const b64 = a => {
    if (!a) return null;
    const u = new Uint8Array(a.buffer, a.byteOffset, a.byteLength);
    let s = "";
    for (let i = 0; i < u.length; i += 32768) s += String.fromCharCode.apply(null, u.subarray(i, i + 32768));
    return btoa(s);
  };
  // settings of a layer: the defaults of the Default configuration, or every mask off
  // masks may also be { cfg: "FOREST", s: { mode: "change" } }: the defaults of that configuration with settings on top
  const settingsFor = (rec, masks) => {
    if (masks && typeof masks === "object") return Object.assign(T.defaults(rec, masks.cfg || "DEFAULT"), masks.s || {});
    const s = T.defaults(rec, "DEFAULT");
    if (masks === "off") Object.assign(s, { cloud: false, shadow: false, terrain: false, illum: false, veg: "off" });
    return s;
  };
  const cfgFor = async (id, date, masks, cc = 100) => {
    const rec = T.LAYER[id], s = settingsFor(rec, masks);
    const scenes = await T.resolveScenes(rec, date, cc, s);
    return { rec, s, scenes, date, cc };
  };
  const plain = v => v == null || typeof v === "function" ? undefined
    : Array.isArray(v) ? v.map(plain) : typeof v === "object" ? Object.fromEntries(Object.entries(v).map(([k, x]) => [k, plain(x)])) : v;
  window.__t = {
    T,
    // the layer records without their functions, and the colour ramps, palettes and constants
    meta() {
      const keep = ["id", "type", "source", "band", "bands", "bg", "min", "max", "threshold", "gainMul", "look", "tci", "metric",
                    "cogScale", "cogFill", "cogMissing", "classify", "def", "name", "modal", "ndwiOpt", "statName", "wms", "steps"];
      const layers = Object.values(T.LAYER).filter(r => !r.ext).map(r => Object.fromEntries(keep.filter(k => r[k] !== undefined && typeof r[k] !== "function")
        .map(k => [k, plain(r[k])]).concat([["rampStops", r.ramp && r.ramp.stops ? plain(r.ramp.stops) : null],
                                             ["domain", r.domain ? plain(r.domain) : null]])));
      const ramps = Object.fromEntries(RAMPS.map(n => { const v = T[n]; return [n, v && v.stops ? { stops: plain(v.stops) } : plain(v)]; }));
      const consts = {};
      ["MISSING_RGB", "CHANGE_RGB", "NOCHANGE_RGB", "SHADOW_RGB", "FDC_PALETTE", "BASE_GAIN", "BASE_GAMMA", "OPT", "ILLUM_THR", "EDGE_M",
       "EDGE_DARK", "MASK_DEFAULTS", "DATA_MAXZOOM", "DECODE_WORKERS"].forEach(n => { try { consts[n] = plain(T[n]); } catch (e) { /* not in this version */ } });
      try { consts.decodePool = !!T.decodePool; } catch (e) { /* not in this version */ }
      const defs = Object.fromEntries(Object.values(T.LAYER).filter(r => !r.ext).map(r => [r.id, plain(T.defaults(r, "DEFAULT"))]));
      return { layers, ramps, consts, defs };
    },
    async scenes(id, date, masks) { const c = await cfgFor(id, date, masks); return c.scenes; },
    async ref(id, date, masks) { const c = await cfgFor(id, date, masks); return plain(await T.resolveRef(c.s, date)); },
    // the map tile as the page draws it (renderTile): RGBA bytes
    async tile(id, date, masks, bbox, W, H) {
      const c = await cfgFor(id, date, masks), t0 = performance.now();
      const im = await T.renderTile(c, bbox, W, H);
      return { scenes: c.scenes, ms: performance.now() - t0, rgba: im ? b64(im.data) : null };
    },
    // the values behind a layer, as the analytical TIFF-32 download and the statistics compute them
    async values(id, date, masks, bbox, W, H) {
      const c = await cfgFor(id, date, masks), rec = c.rec, s = c.s, n = W * H;
      if (!c.scenes.length) return { scenes: [], vals: null };
      if (rec.type === "wincomp") {
        const d = await T.winDiff(c, bbox, W, H);
        return { scenes: c.scenes, vals: b64(Float32Array.from(d.dif)) };
      }
      const grid = { bbox, W, H, mask: new Uint8Array(n).fill(1), n };
      const o = { maskClouds: s.cloud || s.shadow, maskTerrain: s.terrain, maskIllum: s.illum ? s.illumThr : null,
                  cloudCodes: { 1: s.cloud, 2: s.cloud, 3: s.shadow }, veg: s.veg, cmask: "off" };
      if (rec.type === "diff2") Object.assign(o, { firstClear: true, vegDate: date });
      const r = T.statRec(rec), res = await T.sampleAoi(r, c.scenes, grid, o);
      let band = res.vals[0], refScenes = null;
      if (rec.type === "diff2") {
        const ref = await T.resolveRef(s, date);
        refScenes = ref.scenes;
        const rr = await T.sampleAoi(r, ref.scenes, grid, o);
        band = band.map((v, k) => v - rr.vals[0][k]);
      }
      return { scenes: c.scenes, refScenes, vals: b64(band), vals2: res.vals.length > 1 ? res.vals.slice(1).map(b64) : null,
               cls: res.cls ? b64(res.cls) : null, masked: res.masked, shadow: res.shadow, outside: res.outside };
    },
    // a COG read as the page does it (readGrid: overview choice, nearest sampling at the pixel centre)
    async raw(url, bbox, W, H, fill, nb) {
      if (nb) { const a = await T.readGridBands(url, bbox, W, H, undefined, fill, nb); return { bands: a.map(b64), valid: a.valid ? b64(a.valid) : null }; }
      return { band: b64(await T.readGrid(url, bbox, W, H, undefined, fill)) };
    },
    // the URLs the page reads for a layer and scene (COG of a product, S2-SR assets, vegetation mask)
    urls(id, scene, bands, veg) {
      const rec = T.LAYER[id];
      let vegU = null;
      try { if (veg && veg !== "off") vegU = T.vegUrl(T.vegParse(veg), scene.slice(0, 10)); } catch (e) { /* other mask kinds */ }
      return { cog: rec.cogUrl ? rec.cogUrl(scene) : null, veg: vegU,
               assets: Object.fromEntries((bands || []).map(b => [b, T.assetUrl(scene, b)])) };
    }
  };
}
