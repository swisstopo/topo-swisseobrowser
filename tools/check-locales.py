#!/usr/bin/env python3
"""Checks the translations in locales/, and writes the English reference files.

  locales/<lng>/<ns>.json    nested keys, the same tree in every language
    app   swisseo-browser.html
    help  docs/index.html

English is the source and lives in the pages: the text of every element marked data-i18n, the English
argument of every t() / tn() call, and the English of the data the page renders (layer names and
descriptions, highlight stories, configuration names, class labels). --extract reads all of that and
writes locales/en/<ns>.json, so translators see every string and the validation below has a reference.
The English file is never edited by hand; CI fails when it is not what --extract would write.

Checks, for de, fr and it against en:
  errors    invalid JSON; a key English does not have; an empty value; a {{placeholder}} that differs
            from the English; HTML tags that differ from the English; a plural form the language needs and lacks (fr and it have one, many,
            other); a German "ß" (Swiss spelling uses "ss")
  warnings  a key not translated yet (the page shows English there); a protected token of the
            English (band, index, product id, URL) missing from the translation

Usage:
  python3 tools/check-locales.py            validate, print coverage
  python3 tools/check-locales.py --extract  regenerate locales/en/*.json from the pages
  python3 tools/check-locales.py --check    both, writing nothing: what CI runs
"""
import argparse
import json
import os
import re
import sys

LANGS = ["en", "de", "fr", "it"]
PLURALS = {"en": ["one", "other"], "de": ["one", "other"], "fr": ["one", "many", "other"],
           "it": ["one", "many", "other"]}
PAGES = {"app": "swisseo-browser.html", "help": "docs/index.html"}
STR = r'"((?:[^"\\\n]|\\.)*)"'                      # a JavaScript double-quoted string literal
# Kept as they are in every language. A link only has to keep its host: swisstopo's pages have a
# different address per language (/de/satellitenbild-..., /fr/image-satellite-...).
PROTECTED = re.compile(r"\b(?:B0?\d{1,2}A?|NDVI\w*|NDWI|NDMI|NDSI|NBR|NDDI|EVI|SAVI|BSI|VHI|AOT|SCL|TCI|"
                       r"COG|STAC|WMS|WMTS|LV95|swissEO|Sentinel-2)\b|https?://[^/\s)\]\"'<>]+")

errors, warnings = [], []


def err(msg, file=None):
    errors.append(msg)
    print("::error{}::{}".format(" file=" + file if file else "", msg))


def wrn(msg, file=None):
    warnings.append(msg)
    print("::warning{}::{}".format(" file=" + file if file else "", msg))


def js_string(s):
    """The value of a JavaScript string literal body."""
    s = s.replace("\\'", "'")
    try:
        return json.loads('"' + s + '"')
    except ValueError:
        return None


def squash(s):
    return " ".join(s.split())


# ---- English from the markup ----------------------------------------------------------------------

def element_end(html, start, tag):
    """The offset of the closing tag of the element whose opening tag ends at start."""
    depth, i, pat = 1, start, re.compile(r"</?" + tag + r"\b[^>]*>", re.I)
    while depth:
        m = pat.search(html, i)
        if not m:
            return None
        depth += -1 if m.group(0).startswith("</") else 1
        i = m.end()
        if depth == 0:
            return m.start()
    return None


def from_markup(html, where):
    out = {}
    body = re.sub(r"<script\b[\s\S]*?</script>", lambda m: " " * len(m.group(0)), html)
    for m in re.finditer(r'<(\w+)\b([^>]*?\sdata-i18n="([^"]+)"[^>]*)>', body):
        tag, attrs, spec = m.group(1).lower(), m.group(2), m.group(3)
        for part in spec.split(";"):
            part = part.strip()
            if not part:
                continue
            a = re.match(r"^\[([\w-]+)\](.+)$", part)
            target, key = (a.group(1), a.group(2)) if a else ("text", part)
            if target in ("text", "html"):
                end = element_end(body, m.end(), tag)
                if end is None:
                    err("{}: the element of '{}' is not closed".format(where, key), where)
                    continue
                inner = html[m.end():end]
                if target == "text" and "<" in inner:
                    err("{}: '{}' contains markup, so writing its text would delete it. Mark the text "
                        "part only, or use [html]".format(where, key), where)
                    continue
                value = squash(inner)
            else:
                v = re.search(r'\s' + re.escape(target) + r'="([^"]*)"', attrs)
                if not v:
                    err("{}: '{}' is marked for [{}], but the element has no such attribute".format(
                        where, key, target), where)
                    continue
                value = squash(v.group(1))
            add(out, key, value, where)
    return out


# ---- English from the script ----------------------------------------------------------------------

def from_script(html, where):
    out = {}
    lb = r"(?<![\w.$])"
    for m in re.finditer(lb + r't\(\s*"([a-zA-Z][\w.-]*)"\s*,\s*' + STR + r"\s*[,)]", html):
        add(out, m.group(1), js_string(m.group(2)), where)
    for m in re.finditer(lb + r'tn\(\s*"([a-zA-Z][\w.-]*)"\s*,\s*' + STR + r"\s*,\s*" + STR + r"\s*,", html):
        add(out, m.group(1) + "_one", js_string(m.group(2)), where)
        add(out, m.group(1) + "_other", js_string(m.group(3)), where)
    # tset(node, "key", "English"[, "attribute"]): an element the script builds once and marks for apply()
    for m in re.finditer(lb + r'tset\(\s*[^,()]+,\s*"([a-zA-Z][\w.-]*)"\s*,\s*' + STR + r"\s*[,)]", html):
        add(out, m.group(1), js_string(m.group(2)), where)
    # a t() whose English is not one literal cannot be extracted: it would silently lack a reference
    for m in re.finditer(lb + r't\(\s*"([a-zA-Z][\w.-]*)"\s*,(?=\s*[^"\s])', html):
        err("{}: t(\"{}\", ...) must have its English as one string literal".format(where, m.group(1)), where)
    for m in re.finditer(lb + r'tset\(\s*[^,()]+,\s*"([a-zA-Z][\w.-]*)"\s*,(?=\s*[^"\s])', html):
        err("{}: tset(..., \"{}\", ...) must have its English as one string literal".format(where, m.group(1)), where)
    return out


# ---- English of the data the page renders ---------------------------------------------------------

def block(html, start_rx, end_rx):
    a = re.search(start_rx, html, re.M)
    if not a:
        return ""
    b = re.compile(end_rx, re.M).search(html, a.end())
    return html[a.end():b.start() if b else len(html)]


def fields(entry, names):
    got = {}
    for n in names:
        m = re.search(r"\b" + n + r"\s*:\s*" + STR, entry)
        if m:
            got[n] = js_string(m.group(1))
    return got


def from_data(html, where):
    out = {}
    # layers: LAYERS gives name, sub, desc; COP_META overrides name and sub and adds the Markdown
    # description, as Object.assign(LAYER[id], COP_META[id]) does in the page
    layers = {}
    for m in re.finditer(r'^\s*\{ id:"([a-z0-9_]+)"([\s\S]*?)(?=^\s*\{ id:"|^\];)', block(
            html, r"^const LAYERS = \[", r"^\];") + "\n];", re.M):
        layers[m.group(1)] = fields(m.group(2), ["name", "sub", "desc", "note"])
        # the VHI layers take title and abstract from WMS_META (wms.geo.admin.ch GetCapabilities)
        w = re.search(r'name:WMS_META\["([^"]+)"\]\.title', m.group(2))
        if w:
            meta = re.search(r'"' + re.escape(w.group(1)) + r'": \{\s*title: ' + STR + r",\s*abstract: " + STR, html)
            if meta:
                layers[m.group(1)].update(name=js_string(meta.group(1)), desc=js_string(meta.group(2)))
    cop = block(html, r"^const COP_META = \{", r"^\};")
    for m in re.finditer(r"^  (\w+): \{([\s\S]*?)(?=^  \w+: \{|\Z)", cop, re.M):
        layers.setdefault(m.group(1), {}).update(fields(m.group(2), ["name", "sub", "cop"]))
    for lid, f in layers.items():
        if f.get("name"):
            add(out, "layers." + lid + ".name", f["name"], where)
        if f.get("sub"):
            add(out, "layers." + lid + ".subtitle", f["sub"], where)
        desc = f.get("cop") or f.get("desc")
        if desc:
            add(out, "layers." + lid + ".description", desc, where)
        if f.get("note"):
            add(out, "layers." + lid + ".note", f["note"], where)
    # highlight stories
    hl = block(html, r"^const HIGHLIGHTS = \{", r"^\};")
    for m in re.finditer(r'\{ id: "([a-z0-9-]+)"([\s\S]*?)(?=\{ id: "|\Z)', hl):
        f = fields(m.group(2), ["title", "text"])
        for n, v in f.items():
            add(out, "highlights." + m.group(1) + "." + n, v, where)
    # configurations and their group headings (the generated catalogue block)
    cfg = block(html, r"^/\* catalog:configs:start \*/", r"^/\* catalog:configs:end \*/")
    for m in re.finditer(r'^  ([A-Z0-9]+): \{ name: ' + STR, cfg, re.M):
        add(out, "configurations." + m.group(1), js_string(m.group(2)), where)
    for m in re.finditer(r'^    \[' + STR + r", \[", cfg, re.M):
        title = js_string(m.group(1))
        if title:
            add(out, "groups." + slug(title), title, where)
    # class labels, by their code
    for name, key in (("P_SCL", "scl"), ("P_CLOUD", "cloud"), ("FDC_PALETTE", "fdc")):
        for m in re.finditer(r"(\d+)\s*:\s*\[\s*" + STR, block(html, r"^const " + name + r" = \{", r"\};")):
            add(out, "classes." + key + "." + m.group(1), js_string(m.group(2)), where)
    for i, m in enumerate(re.finditer(r"\[\s*" + STR + r"\s*,\s*hx\(", block(html, r"^const VHI_CLASSES = \[", r"^\];"))):
        add(out, "classes.vhi." + str(i), js_string(m.group(1)), where)
    # class labels of a layer's own classification (classify: [[limit, rgb, "label"], ...]), where they are words
    for m in re.finditer(r'^\s*\{ id:"([a-z0-9_]+)"([\s\S]*?)(?=^\s*\{ id:"|^\];)', block(
            html, r"^const LAYERS = \[", r"^\];") + "\n];", re.M):
        c = re.search(r"classify:\[([\s\S]*?)\]\],", m.group(2))
        if c:
            for i, s in enumerate(re.finditer(r"\]\s*,\s*" + STR + r"\s*\]", c.group(1) + "]]")):
                if re.search(r"[a-z]{2}", js_string(s.group(1))):
                    add(out, "classes." + m.group(1) + "." + str(i), js_string(s.group(1)), where)
    # mask vocabularies, by their code
    for name, key in (("TLM_CLASSES", "tlm"), ("LEAF_TYPE", "leaf"), ("LFI_BASE", "lfiBase"), ("VEG_KIND", "veg"),
                      ("BASE_NAMES", "basemap")):
        for m in re.finditer(r"(\w+)\s*:\s*" + STR, block(html, r"^const " + name + r" = \{", r"\};")):
            add(out, "vocab." + key + "." + m.group(1), js_string(m.group(2)), where)
    for m in re.finditer(r'\[\s*"(\w+)"\s*,\s*' + STR + r"\s*,\s*\[", block(html, r"^const ETH_CLASSES = \[", r"\]\];")):
        add(out, "vocab.eth." + m.group(1), js_string(m.group(2)), where)
    for m in re.finditer(r'\{\s*k:\s*"(\w+)"\s*,\s*name:\s*' + STR, block(html, r"^const LNF = \[", r"\}\];")):
        add(out, "vocab.lnf." + m.group(1), js_string(m.group(2)), where)
    return out


def slug(s):
    return re.sub(r"^-|-$", "", re.sub(r"[^a-z0-9]+", "-", s.lower()))


# ---- nested key trees -----------------------------------------------------------------------------

def add(tree, key, value, where):
    if value is None:
        err("{}: the English of '{}' could not be read".format(where, key), where)
        return
    node, parts = tree, key.split(".")
    for p in parts[:-1]:
        nxt = node.setdefault(p, {})
        if not isinstance(nxt, dict):
            err("{}: '{}' is both a text and a group of keys; rename one".format(where, key), where)
            return
        node = nxt
    old = node.get(parts[-1])
    if isinstance(old, dict):
        err("{}: '{}' is both a group of keys and a text; rename one".format(where, key), where)
    elif old is not None and old != value:
        err("{}: '{}' has two different English texts:\n  {!r}\n  {!r}".format(where, key, old, value), where)
    else:
        node[parts[-1]] = value


def flat(tree, prefix=""):
    out = {}
    for k, v in tree.items():
        if isinstance(v, dict):
            out.update(flat(v, prefix + k + "."))
        else:
            out[prefix + k] = v
    return out


def extract(ns):
    path = PAGES[ns]
    with open(path, encoding="utf8") as f:
        html = f.read()
    tree = {}
    for part in (from_markup(html, path), from_script(html, path), from_data(html, path) if ns == "app" else {}):
        for k, v in flat(part).items():
            add(tree, k, v, path)
    return tree


def dump(tree):
    return json.dumps(tree, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


# ---- validation -----------------------------------------------------------------------------------

def placeholders(s):
    return sorted(set(re.findall(r"\{\{\s*(\w+)\s*\}\}", s)))


def tags(s):
    """The HTML tags of a value: a translation keeps every element of its English (in any order)."""
    return sorted(re.findall(r"</?[a-zA-Z][\w-]*", s))


def validate(ns, en):
    en_flat = flat(en)
    base = {re.sub(r"_(one|many|other)$", "", k) for k in en_flat if re.search(r"_(one|other)$", k)}
    report = []
    for lng in LANGS[1:]:
        path = "locales/{}/{}.json".format(lng, ns)
        if not os.path.exists(path):
            wrn("{} does not exist yet: everything shows English".format(path), path)
            report.append((lng, 0, len(en_flat)))
            continue
        try:
            with open(path, encoding="utf8") as f:
                tr = flat(json.load(f))
        except ValueError as e:
            err("{} is not valid JSON: {}".format(path, e), path)
            continue
        done = 0
        for k, v in tr.items():
            stem = re.sub(r"_(one|many|other)$", "", k)
            if k not in en_flat and not (stem in base and k.endswith(("_many",))):
                err("{}: '{}' is not a key of the English".format(path, k), path)
                continue
            if not isinstance(v, str) or not v.strip():
                err("{}: '{}' is empty; leave a key out instead, the page then shows English".format(path, k), path)
                continue
            ref = en_flat.get(k) or en_flat.get(stem + "_other", "")
            if placeholders(v) != placeholders(ref):
                err("{}: '{}' has the placeholders {} but the English has {}".format(
                    path, k, placeholders(v), placeholders(ref)), path)
            if tags(v) != tags(ref):
                err("{}: '{}' has the markup {} but the English has {}".format(
                    path, k, " ".join(tags(v)) or "none", " ".join(tags(ref)) or "none"), path)
            if lng == "de" and "ß" in v:
                err("{}: '{}' contains ß; Swiss German writes ss".format(path, k), path)
            missing = sorted(set(PROTECTED.findall(ref)) - set(PROTECTED.findall(v)))
            if missing:
                wrn("{}: '{}' lacks {} of the English (not translated by rule)".format(
                    path, k, ", ".join(missing)), path)
        for stem in sorted(base):
            if any(k.startswith(stem + "_") for k in tr):
                for form in PLURALS[lng]:
                    if stem + "_" + form not in tr:
                        err("{}: '{}_{}' is missing; {} needs the forms {}".format(
                            path, stem, form, lng, ", ".join(PLURALS[lng])), path)
        done = sum(1 for k in en_flat if k in tr)
        report.append((lng, done, len(en_flat)))
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--extract", action="store_true", help="regenerate locales/en/*.json")
    ap.add_argument("--check", action="store_true", help="validate, and fail when locales/en is stale")
    args = ap.parse_args()

    for ns in PAGES:
        en = extract(ns)
        path = "locales/en/{}.json".format(ns)
        text = dump(en)
        if args.extract:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf8", newline="\n") as f:
                f.write(text)
            print("{}: {} strings".format(path, len(flat(en))))
        elif args.check:
            current = open(path, encoding="utf8").read() if os.path.exists(path) else ""
            if current != text:
                err("{} is not what the pages say. Run 'python3 tools/check-locales.py --extract' and "
                    "commit the result.".format(path), path)
        for lng, done, total in validate(ns, en):
            print("{:4} {:3}: {:4} of {:4} translated".format(ns, lng, done, total))
    if errors:
        print("{} errors, {} warnings".format(len(errors), len(warnings)))
        sys.exit(1)
    print("locales OK ({} warnings)".format(len(warnings)))


if __name__ == "__main__":
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    main()
