#!/usr/bin/env python3
"""Writes the catalogue of catalog/ into the page and into the checklist of README.md.

  catalog/layers.yaml          which layers exist and whether they are verified
  catalog/configurations.yaml  what the pull-down offers, in which order, in which groups

The layer definitions themselves (bands, formulas, colour ramps, JavaScript) stay in
swisseo-browser.html; this script only decides what is offered where.

  --env int    everything, as on GitHub Pages
  --env prod   without the configurations marked beta and without the layers that are not
               verified: production offers only what has been checked

What it writes:
  * the block between /* catalog:configs:start */ and /* catalog:configs:end */ in every page
    given with --page,
  * the line "const VERIFIED_IDS = null; // replaced on deploy" in the same pages, which decides
    the BETA labels (it keeps the exact shape the production smoke test greps for),
  * with --write-readme, the checklist between <!-- verification:start --> and <!-- verification:end -->,
  * with --previews FILE, the thumbnails of the layers that are offered, one per line.

  --check verifies that the files in the repository are what this script would write, and that every
  thumbnail the page names is in public/previews/, and exits 1
  with an annotation otherwise. That is how a hand edit of a generated block is caught in CI.

Usage:
  python3 tools/build-catalog.py --env int  --page _site/index.html --page _site/swisseo-browser.html
  python3 tools/build-catalog.py --env prod --page _site/index.html --previews previews.txt
  python3 tools/build-catalog.py --env int  --write-readme      (after editing catalog/)
  python3 tools/build-catalog.py --env int  --check             (in CI)
"""
import argparse
import json
import os
import re
import sys

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is needed: python3 -m pip install 'PyYAML==6.0.3'")

PAGE = "swisseo-browser.html"
README = "README.md"
CFG_START = "/* catalog:configs:start */"
CFG_END = "/* catalog:configs:end */"
VER_MARKER = "const VERIFIED_IDS = null; // replaced on deploy"
VER_WRITTEN = 'const VERIFIED_IDS = {ids}; // from catalog/layers.yaml'
RM_START = "<!-- verification:start -->"
RM_END = "<!-- verification:end -->"

errors = []


def fail(msg, file=None):
    errors.append(msg)
    print("::error{}::{}".format(" file=" + file if file else "", msg))


def load():
    """Reads both catalogue files and checks them against the layer ids in the page."""
    with open("catalog/layers.yaml", encoding="utf8") as f:
        layers = yaml.safe_load(f)["layers"]
    with open("catalog/configurations.yaml", encoding="utf8") as f:
        configs = yaml.safe_load(f)["configurations"]

    # YAML 1.1 reads a bare  true  as a boolean, and "true" is a layer id: every id must be quoted.
    for rec in layers:
        if not isinstance(rec.get("id"), str):
            fail("catalog/layers.yaml: the id {!r} is not text. Quote every id, "
                 "otherwise YAML turns true/yes/no into a boolean.".format(rec.get("id")),
                 "catalog/layers.yaml")
    for c in configs:
        for g in c.get("groups", []):
            for lid in g.get("layers", []):
                if not isinstance(lid, str):
                    fail("catalog/configurations.yaml: the layer id {!r} in {} is not text. "
                         "Quote every id.".format(lid, c.get("key")), "catalog/configurations.yaml")
    if errors:
        sys.exit(1)

    with open(PAGE, encoding="utf8") as f:
        page = f.read()
    in_page = re.findall(r'^\s*\{ id:"([a-z0-9_]+)"', page, re.M)

    listed = [rec["id"] for rec in layers]
    for lid in sorted(set(in_page) - set(listed)):
        fail("the layer '{}' is defined in the page but missing from catalog/layers.yaml".format(lid),
             "catalog/layers.yaml")
    for lid in sorted(set(listed) - set(in_page)):
        fail("catalog/layers.yaml lists '{}', which is not a layer of the page".format(lid),
             "catalog/layers.yaml")
    if len(listed) != len(set(listed)):
        fail("catalog/layers.yaml lists a layer twice", "catalog/layers.yaml")

    keys = [c["key"] for c in configs]
    if len(keys) != len(set(keys)):
        fail("catalog/configurations.yaml uses a key twice", "catalog/configurations.yaml")
    for c in configs:
        if not re.fullmatch(r"[A-Z0-9]+", c["key"]):
            fail("the configuration key '{}' must be upper case without dashes: it is the themeId "
                 "of a permalink".format(c["key"]), "catalog/configurations.yaml")
        for g in c.get("groups", []):
            for lid in g.get("layers", []):
                if lid not in listed:
                    fail("the configuration '{}' uses the layer '{}', which is not in "
                         "catalog/layers.yaml".format(c["key"], lid), "catalog/configurations.yaml")
    used = {lid for c in configs for g in c.get("groups", []) for lid in g.get("layers", [])}
    for lid in sorted(set(listed) - used):
        print("::warning file=catalog/configurations.yaml::the layer '{}' is in no configuration, "
              "so nobody can reach it".format(lid))

    if errors:
        sys.exit(1)
    return layers, configs, page


def published(layers, configs, env):
    """The configurations and verified ids of one environment."""
    verified = {rec["id"] for rec in layers if rec.get("verified")}
    if env == "int":
        return configs, verified

    out = []
    for c in configs:
        if c.get("beta"):
            continue
        groups = []
        for g in c.get("groups", []):
            keep = [lid for lid in g.get("layers", []) if lid in verified]
            if keep:
                groups.append({"title": g.get("title", ""), "layers": keep})
        if not groups:
            print("::warning file=catalog/configurations.yaml::the configuration '{}' has no "
                  "verified layer and is not offered in production".format(c["key"]))
            continue
        d = dict(c)
        d["groups"] = groups
        out.append(d)
    if not out:
        fail("no configuration is left for production: tick at least one layer as verified",
             "catalog/layers.yaml")
        sys.exit(1)
    return out, verified


def configs_block(configs):
    """The generated JavaScript between the two markers."""
    lines = [CFG_START, "const CONFIGS = {"]
    for c in configs:
        head = '  {}: {{ name: {}, beta: {}'.format(c["key"], json.dumps(c["name"]),
                                                    "true" if c.get("beta") else "false")
        if c.get("highlights"):
            head += ", highlights: HIGHLIGHTS." + c["highlights"]
        lines.append(head + ", groups: [")
        groups = c.get("groups", [])
        for i, g in enumerate(groups):
            ids = ", ".join(json.dumps(x) for x in g["layers"])
            # close the ids array, the [title, ids] pair and, on the last group, the groups array
            end = "]]] }," if i == len(groups) - 1 else "]],"
            lines.append("    [{}, [{}{}".format(json.dumps(g.get("title", "")), ids, end))
    lines.append("};")
    lines.append(CFG_END)
    return "\n".join(lines)


def replace_block(text, start, end, new, where):
    a, b = text.find(start), text.find(end)
    if a < 0 or b < a:
        fail("the markers {} .. {} are missing from {}".format(start, end, where), where)
        sys.exit(1)
    return text[:a] + new + text[b + len(end):]


def readme_block(layers, configs):
    """The checklist of README.md, with the configurations of each layer derived."""
    where = {}
    for c in configs:
        for g in c.get("groups", []):
            for lid in g.get("layers", []):
                where.setdefault(lid, []).append(c["name"])
    out = [RM_START]
    for rec in layers:
        names = ", ".join(dict.fromkeys(where.get(rec["id"], [])))
        line = "- [{}] `{}`: {}".format("x" if rec.get("verified") else " ", rec["id"], rec["label"])
        if names:
            line += " *({})*".format(names)
        if rec.get("note"):
            line += ", " + rec["note"]
        out.append(line)
    out.append(RM_END)
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", choices=["int", "prod"], required=True)
    ap.add_argument("--page", action="append", default=[], help="a page to write, repeatable")
    ap.add_argument("--write-readme", action="store_true", help="regenerate the checklist in README.md")
    ap.add_argument("--previews", metavar="FILE", help="write the thumbnails of the offered layers here")
    ap.add_argument("--check", action="store_true", help="write nothing, fail on any difference")
    args = ap.parse_args()

    layers, configs, page = load()
    offered, verified = published(layers, configs, args.env)
    block = configs_block(offered)
    ids = sorted(verified)

    if args.check:
        # the repository files must be what this script would write for integration
        want = configs_block(published(layers, configs, "int")[0])
        a, b = page.find(CFG_START), page.find(CFG_END)
        if a < 0 or b < 0:
            fail("the catalogue markers are missing from " + PAGE, PAGE)
        elif page[a:b + len(CFG_END)] != want:
            fail("the catalogue block in {} is not what catalog/ says. Run "
                 "'python3 tools/build-catalog.py --env int --write-readme' and commit the result, "
                 "or undo the hand edit.".format(PAGE), PAGE)
        with open(README, encoding="utf8") as f:
            readme = f.read()
        ra, rb = readme.find(RM_START), readme.find(RM_END)
        if ra < 0 or rb < 0:
            fail("the checklist markers are missing from " + README, README)
        elif readme[ra:rb + len(RM_END)] != readme_block(layers, configs):
            fail("the checklist in README.md is not what catalog/layers.yaml says. Tick layers in "
                 "catalog/layers.yaml, then run 'python3 tools/build-catalog.py --env int "
                 "--write-readme' and commit the result.", README)
        # every thumbnail the page names must be in public/previews/ (only those are kept there)
        for thumb in sorted(set(re.findall(r'\bthumb:\s*"([^"]+)"', page))):
            if not os.path.isfile(os.path.join("public", "previews", thumb)):
                fail("the thumbnail public/previews/{0} named in {1} is missing. Copy it from the upstream "
                     "Copernicus Browser: git fetch upstream "
                     "--no-tags && git restore --source=upstream/main public/previews/{0}".format(thumb, PAGE), PAGE)
        if errors:
            sys.exit(1)
        print("catalogue OK: {} layers ({} verified), {} configurations".format(
            len(layers), len(ids), len(configs)))
        return

    for f in args.page:
        with open(f, encoding="utf8") as fh:
            s = fh.read()
        s = replace_block(s, CFG_START, CFG_END, block, f)
        if VER_MARKER not in s:
            fail("the VERIFIED_IDS marker is missing from " + f, f)
            sys.exit(1)
        s = s.replace(VER_MARKER, VER_WRITTEN.format(ids=json.dumps(ids)))
        with open(f, "w", encoding="utf8") as fh:
            fh.write(s)

    if args.write_readme:
        with open(README, encoding="utf8") as fh:
            readme = fh.read()
        readme = replace_block(readme, RM_START, RM_END, readme_block(layers, configs), README)
        with open(README, "w", encoding="utf8") as fh:
            fh.write(readme)
        # and the page in the repository, so what is committed matches the catalogue
        with open(PAGE, encoding="utf8") as fh:
            s = fh.read()
        s = replace_block(s, CFG_START, CFG_END, configs_block(published(layers, configs, "int")[0]), PAGE)
        with open(PAGE, "w", encoding="utf8") as fh:
            fh.write(s)

    if args.previews:
        offered_ids = {lid for c in offered for g in c["groups"] for lid in g["layers"]}
        thumbs = []
        for lid in sorted(offered_ids):
            m = re.search(r'^\s*{}:\s*\{{[^\n]*thumb:\s*"([^"]+)"'.format(re.escape(lid)), page, re.M)
            if m:
                thumbs.append(m.group(1))
        with open(args.previews, "w", encoding="utf8") as fh:
            fh.write("\n".join(sorted(set(thumbs))) + "\n")
        print("previews: {} thumbnails for {} offered layers".format(len(set(thumbs)), len(offered_ids)))

    n_layers = len({lid for c in offered for g in c["groups"] for lid in g["layers"]})
    print("{}: {} configurations, {} layers offered, {} of {} verified".format(
        args.env, len(offered), n_layers, len(ids), len(layers)))


if __name__ == "__main__":
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    main()
