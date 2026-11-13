#!/usr/bin/env bash
# Checks an assembled site before deploy: the page must serve its libraries itself.
# Usage: tools/check-dist.sh _site
# 1. Every lib/ file the page references exists in the site.
# 2. No static script or stylesheet tag loads from a CDN (lines starting a real tag; the inline
#    document.write fallbacks for a lone file:// copy of the page are strings inside a script).
# 3. The CDN hostnames appear exactly as often as the file:// fallbacks and prose mentions require.
#    When a library is added or removed, recount with e.g.
#      grep -c 'cdn\.jsdelivr\.net' _site/index.html
#    and update the numbers below: jsDelivr = LIB_CDN entries (11) + CSS onerror fallback (1) +
#    document.write fallbacks (2); cdnjs = LIB_CDN JSZip (1); raw.githubusercontent = LIB_CDN
#    provider list (1) + README fallback (1) + two prose mentions of CORS examples (2).
set -euo pipefail
site=${1:?usage: check-dist.sh <site dir>}
page=$site/index.html

# The page names a library either as a path in a tag (href="lib/x.css") or as a key of its LIB_CDN map,
# which libUrl() resolves to lib/ over http(s). Both must exist in the assembled site.
{ grep -oE '"lib/[^"]+"' "$page" | tr -d '"'
  grep -oE 'libUrl\("[^"]+"\)' "$page" | sed -E 's/libUrl\("(.*)"\)/lib\/\1/'
} | sort -u | while read -r f; do
  [ -f "$site/$f" ] || { echo "::error::$f is referenced by the page but missing from the site"; exit 1; }
done

! grep -qE '^<script src="https://' "$page" ||
  { echo "::error::a static script tag loads from a CDN"; exit 1; }
! grep -qE '<link rel="stylesheet" href="https://' "$page" ||
  { echo "::error::a stylesheet loads from a CDN"; exit 1; }

for h in 'cdn.jsdelivr.net:14' 'cdnjs.cloudflare.com:1' 'raw.githubusercontent.com:4'; do
  host=${h%%:*}; want=${h##*:}
  n=$(grep -o -F "$host" "$page" | wc -l)
  [ "$n" -eq "$want" ] ||
    { echo "::error::$host appears $n times in the page, expected $want (file:// fallbacks and prose only)"; exit 1; }
done
echo "dist check OK: all libraries self-hosted, CDN URLs are fallbacks only"

# 4. Environment: only the integration version may carry a noindex tag, and the integration bar must
#    be switchable in both the page and the help page (the production hosts are listed in each file).
env=${2:-}
if [ -n "$env" ]; then
  # the catalogue must have been written into the page: a forgotten build step is caught here and
  # not by a visitor whose layer list is empty
  grep -q '^const VERIFIED_IDS = \[' "$page" ||
    { echo "::error::the page still has the VERIFIED_IDS placeholder: tools/build-catalog.py did not run"; exit 1; }
  grep -q '^const CONFIGS = {' "$page" ||
    { echo "::error::the page has no configurations"; exit 1; }
  for f in "$page" "$site/docs/index.html"; do
    [ -f "$f" ] || continue
    if [ "$env" = int ]; then
      grep -q '^<meta name="robots" content="noindex, nofollow">$' "$f" ||
        { echo "::error::$f carries no noindex tag, but the integration version must not be indexed"; exit 1; }
    else
      # production keeps the marker comment untouched; what it must not have is the tag itself
      ! grep -q 'name="robots"' "$f" ||
        { echo "::error::$f carries a robots tag: production must stay indexable"; exit 1; }
    fi
    grep -q 'swisseobrowser.swisstopo.admin.ch' "$f" ||
      { echo "::error::$f does not name the production host, so it cannot hide the integration bar"; exit 1; }
    grep -q 'id="envbar"' "$f" ||
      { echo "::error::$f has no integration bar"; exit 1; }
  done
  # the link preview image must exist in the site, whatever address the tag carries
  img=$(grep -oE 'property="og:image" content="[^"]+"' "$page" | sed -E 's/.*content="(.*)"/\1/' |
        sed -E 's#^https?://[^/]+/##; s#^topo-swisseobrowser/##')
  [ -f "$site/$img" ] ||
    { echo "::error::the link preview image $img is referenced but missing from the site"; exit 1; }
  echo "environment check OK ($env)"
fi
