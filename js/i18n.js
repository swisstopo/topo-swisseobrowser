/* swissEO Browser: languages (i18next). Shared by swisseo-browser.html and docs/index.html.

   English is the source and lives in the pages themselves: the text of every marked element and the
   English argument of every t() call. locales/en/<ns>.json is generated from that for translators
   (tools/check-locales.py --extract); only the chosen other language is fetched, from
   locales/<lng>/<ns>.json. So a failed request, a missing key or a page opened from disk (where
   fetch cannot read local files) always shows English, never a raw key or a blank.

   Markup:  data-i18n="key"                    text
            data-i18n="[title]key;[aria-label]k2"  attributes, separated by ";"
            data-i18n="[html]key"              our own text with links or emphasis
   Script:  t("key", "English")                tn("key", "one layer", "{{count}} layers", n)

   A classic script on purpose: it must also load from disk, where module scripts are blocked. When
   i18next itself is missing (a lone copy of the page) everything falls back to English. */
(function () {
  "use strict";
  var ALL = ["en", "de", "fr", "it"];
  var NAMES = { en: "EN", de: "DE", fr: "FR", it: "IT" };
  var LOCALE = { en: "en-GB", de: "de-CH", fr: "fr-CH", it: "it-CH" };
  var STORE = "swisseo.lang";

  var i18n = window.i18next || null;
  var ready = false, lang = "en", ns = "app", base = "./locales/", offered = ALL.slice();
  var listeners = [], english = new WeakMap(), warned = Object.create(null);

  function prodHost() { return document.documentElement.dataset.env === "prod"; }

  function warn(msg) {
    if (warned[msg]) return;
    warned[msg] = true;
    if (window.console) console.warn("[swissEO i18n] " + msg);
  }

  /* lang= in the address, then the earlier choice in this browser, then what the browser asks for */
  function pick() {
    var q = new URLSearchParams(location.search).get("lang");
    if (q && offered.indexOf(q) >= 0) return q;
    var s = null;
    try { s = localStorage.getItem(STORE); } catch (e) { /* private mode, blocked storage */ }
    if (s && offered.indexOf(s) >= 0) return s;
    var list = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || ""];
    for (var i = 0; i < list.length; i++) {
      var b = String(list[i]).slice(0, 2).toLowerCase();
      if (offered.indexOf(b) >= 0) return b;
    }
    return "en";
  }

  function load(lng) {
    if (lng === "en" || (i18n && i18n.hasResourceBundle(lng, ns))) return Promise.resolve(true);
    var url = base + lng + "/" + ns + ".json";
    return fetch(url, { cache: "no-cache" })
      .then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
      .then(function (data) { i18n.addResourceBundle(lng, ns, data, true, true); return true; })
      .catch(function (e) {
        warn("could not load " + url + " (" + e.message + "); showing English" +
             (location.protocol === "file:" ? ". A page opened from disk cannot read local files: serve the folder, e.g. python -m http.server" : ""));
        return false;
      });
  }

  /* the translation, or the English the caller passes in */
  function t(key, en, opts) {
    if (!ready || lang === "en") return interpolate(en, opts);
    var o = Object.assign({}, opts || {}, { defaultValue: en });
    return i18n.t(key, o);
  }

  /* with a count: i18next picks the plural form of the language (French and Italian have three) */
  function tn(key, one, other, count, opts) {
    var o = Object.assign({}, opts || {}, { count: count });
    if (!ready || lang === "en") return interpolate(count === 1 ? one : other, o);
    o.defaultValue = other;
    o.defaultValue_one = one;
    o.defaultValue_other = other;
    return i18n.t(key, o);
  }

  /* English needs no i18next, only {{name}} filled in */
  function interpolate(s, o) {
    if (s == null || !o) return s;
    return String(s).replace(/\{\{\s*(\w+)\s*\}\}/g, function (m, k) { return o[k] != null ? o[k] : m; });
  }

  /* Writes the current language into every marked element below root. */
  function apply(root) {
    root = root || document;
    var els = Array.prototype.slice.call(root.querySelectorAll("[data-i18n]"));
    if (root.nodeType === 1 && root.hasAttribute("data-i18n")) els.unshift(root);
    for (var i = 0; i < els.length; i++) {
      var el = els[i], keep = english.get(el) || {};
      el.getAttribute("data-i18n").split(";").forEach(function (part) {
        part = part.trim();
        if (!part) return;
        var m = /^\[([\w-]+)\](.+)$/.exec(part), target = m ? m[1] : "text", key = m ? m[2] : part;
        if (!(target in keep)) {
          keep[target] = target === "text" ? el.textContent : target === "html" ? el.innerHTML : (el.getAttribute(target) || "");
        }
        var v = t(key, keep[target]);
        if (target === "text") el.textContent = v;
        else if (target === "html") el.innerHTML = v;
        else el.setAttribute(target, v);
      });
      english.set(el, keep);
    }
  }

  function setLanguage(lng, remember) {
    if (offered.indexOf(lng) < 0) lng = "en";
    return load(lng).then(function (ok) {
      if (!ok) lng = "en";
      lang = lng;
      if (ready) i18n.changeLanguage(lng);
      document.documentElement.lang = lng;
      if (remember) { try { localStorage.setItem(STORE, lng); } catch (e) { /* not stored */ } }
      apply(document);
      listeners.forEach(function (fn) { try { fn(lng); } catch (e) { warn("a refresh after the language change failed: " + e.message); } });
      return lng;
    });
  }

  /* Starts the languages of one page. offeredList: the languages this build offers (null = all). */
  function init(options) {
    options = options || {};
    ns = options.namespace || "app";
    base = options.base || "./locales/";
    offered = (options.offered || ALL).filter(function (l) { return ALL.indexOf(l) >= 0; });
    if (offered.indexOf("en") < 0) offered.unshift("en");
    var lng = pick();
    if (!i18n) {
      warn("i18next is not loaded; the page stays English");
      document.documentElement.lang = "en";
      return Promise.resolve("en");
    }
    var dev = !prodHost();
    return i18n.init({
      lng: "en", fallbackLng: "en", supportedLngs: ALL, ns: [ns], defaultNS: ns, resources: {},
      returnEmptyString: false, returnNull: false, interpolation: { escapeValue: false },
      /* development check: every key the current language lacks is named once in the console */
      saveMissing: dev,
      missingKeyHandler: function (lngs, n, key) {
        if (dev && lang !== "en") warn("missing in " + lang + "/" + n + ".json: " + key);
      }
    }).then(function () {
      ready = true;
      return setLanguage(lng, false);
    });
  }

  function locale() { return LOCALE[lang] || "en-GB"; }

  /* Formatting for the screen only: exports, links and coordinates keep their machine format. */
  function fmtNumber(v, opts) { return new Intl.NumberFormat(locale(), opts).format(v); }
  function fmtDate(d, opts) { return new Intl.DateTimeFormat(locale(), Object.assign({ timeZone: "UTC" }, opts)).format(d); }
  function monthNames(style) {
    var out = [];
    for (var m = 0; m < 12; m++) out.push(fmtDate(new Date(Date.UTC(2026, m, 1)), { month: style || "long" }));
    return out;
  }
  /* Monday first, as in Switzerland */
  function weekdayNames(style) {
    var out = [];
    for (var d = 0; d < 7; d++) out.push(fmtDate(new Date(Date.UTC(2026, 10, 2 + d)), { weekday: style || "short" }));
    return out;
  }

  window.swisseoI18n = {
    init: init, setLanguage: setLanguage, apply: apply, t: t, tn: tn,
    onChange: function (fn) { listeners.push(fn); },
    lang: function () { return lang; }, locale: locale,
    offered: function () { return offered.slice(); }, names: NAMES,
    fmtNumber: fmtNumber, fmtDate: fmtDate, monthNames: monthNames, weekdayNames: weekdayNames
  };
})();
