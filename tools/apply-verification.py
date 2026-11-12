"""Injects the layer verification checklist of README.md into the assembled pages.

Usage: python3 tools/apply-verification.py _site/index.html [_site/swisseo-browser.html ...]
Run from the repository root by both deploy workflows (GitHub Pages and production). Replaces the
VERIFIED_IDS marker in each target file with the checked ids, and warns when the checklist and the
layers of the page drift apart. Without this step the deployed page would fetch README.md at runtime.
"""
import json
import re
import sys

if len(sys.argv) < 2:
    sys.exit("usage: apply-verification.py <page.html> [<page.html> ...]")

md = open("README.md", encoding="utf8").read()
a, b = md.find("<!-- verification:start -->"), md.find("<!-- verification:end -->")
if a < 0 or b < a:
    sys.exit("README.md: verification markers not found")
listed, checked = [], []
for line in md[a:b].splitlines():
    m = re.match(r"\s*[-*] \[([ xX])\] `([a-z0-9_]+)`", line)
    if m:
        listed.append(m.group(2))
        if m.group(1) != " ":
            checked.append(m.group(2))

page = open("swisseo-browser.html", encoding="utf8").read()
layers = re.findall(r'^\s*\{ id:"([a-z0-9_]+)"', page, re.M)
for i in sorted(set(layers) - set(listed)):
    print(f"::warning file=README.md::layer '{i}' is missing in the verification checklist")
for i in sorted(set(listed) - set(layers)):
    print(f"::warning file=README.md::'{i}' in the verification checklist is not a layer of the page")

marker = "const VERIFIED_IDS = null; // replaced on deploy"
for f in sys.argv[1:]:
    s = open(f, encoding="utf8").read()
    if marker not in s:
        sys.exit(f"{f}: VERIFIED_IDS marker not found")
    s = s.replace(marker, "const VERIFIED_IDS = " + json.dumps(checked) + "; // from README.md")
    open(f, "w", encoding="utf8").write(s)
print(f"verified: {len(checked)} of {len(listed)} layers: {', '.join(checked) or '-'}")
