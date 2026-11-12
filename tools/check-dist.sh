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
