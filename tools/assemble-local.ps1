# Assembles one of the two sites locally, exactly as the workflows do, so a change can be looked at
# before it is pushed. Needs PyYAML (python3 -m pip install "PyYAML==6.0.3").
#
#   powershell -File tools/assemble-local.ps1 -Env int  -Out _int
#   powershell -File tools/assemble-local.ps1 -Env prod -Out _prod
#
# Then serve the folder, e.g.  cd _int; python -m http.server 8000
param(
  [ValidateSet("int", "prod")][string]$Env = "int",
  [string]$Out = "_site",
  [string]$Site = "https://d2i2rebzl46jfr.cloudfront.net"   # only used for prod: the link preview
)
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

# Empty the folder rather than delete it: a shell sitting in it holds a handle on Windows and the
# delete then fails, which would stop the build for no good reason.
if (Test-Path $Out) {
  Get-ChildItem -Force $Out | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
}
New-Item -ItemType Directory -Force -Path "$Out/public/previews" | Out-Null

Copy-Item swisseo-browser.html "$Out/index.html"
if ($Env -eq "int") { Copy-Item swisseo-browser.html "$Out/swisseo-browser.html" }
Copy-Item README.md "$Out/README.md"
Copy-Item -Recurse docs "$Out/docs"
Copy-Item -Recurse lib "$Out/lib"
Copy-Item -Recurse js "$Out/js"
Copy-Item -Recurse locales "$Out/locales"

# the thumbnails of the layers this build offers
$prev = Join-Path $env:TEMP "previews-$Env.txt"
& python tools/build-catalog.py --env $Env --previews $prev
Get-Content $prev | Where-Object { $_ } | ForEach-Object { Copy-Item "public/previews/$_" "$Out/public/previews/" }

# the catalogue, into every page of this build
$pages = @("$Out/index.html")
if ($Env -eq "int") { $pages += "$Out/swisseo-browser.html" }
$args = @("tools/build-catalog.py", "--env", $Env)
foreach ($p in $pages) { $args += @("--page", $p) }
& python @args

# The files are UTF-8 and the pages contain French and German text. Get-Content / Set-Content would
# read them in the system code page and write mojibake ("ConfÃ©dÃ©ration"), so read and write them
# explicitly as UTF-8 without a byte order mark, which is what the Linux runners produce with sed.
$utf8 = New-Object System.Text.UTF8Encoding($false)
function Edit-Utf8([string]$Path, [scriptblock]$Change) {
  $full = (Resolve-Path $Path).Path
  $text = [System.IO.File]::ReadAllText($full, $utf8)
  [System.IO.File]::WriteAllText($full, (& $Change $text), $utf8)
}

if ($Env -eq "int") {
  # keep the integration version out of search engines
  foreach ($f in $pages + @("$Out/docs/index.html")) {
    Edit-Utf8 $f { param($t) $t -replace '(?m)^<!-- robots:marker.*?-->\r?$',
      '<meta name="robots" content="noindex, nofollow">' }
  }
} else {
  # point the link preview at this site
  foreach ($f in @("$Out/index.html", "$Out/docs/index.html")) {
    Edit-Utf8 $f { param($t) $t.Replace("https://swisstopo.github.io/topo-swisseobrowser", $Site) }
  }
  # production offers only the reviewed languages: the list is the `offered=` line of deploy-prod.yml
  $m = Select-String -Path ".github/workflows/deploy-prod.yml" -Pattern "^\s*offered='(\[[^\]]*\])'" | Select-Object -First 1
  if (-not $m) { throw "deploy-prod.yml has no offered='[...]' line" }
  $offered = $m.Matches[0].Groups[1].Value
  foreach ($f in @("$Out/index.html", "$Out/docs/index.html")) {
    Edit-Utf8 $f { param($t) $t.Replace("const LANGS_OFFERED = null; // replaced on deploy",
      "const LANGS_OFFERED = $offered; // offered in production") }
  }
}

# check-dist.sh is a shell script: run it with Git's bash when it is not on PATH
$bash = (Get-Command bash -ErrorAction SilentlyContinue).Source
if (-not $bash) { $bash = "C:\Program Files\Git\bin\bash.exe" }
if (Test-Path $bash) { & $bash tools/check-dist.sh $Out $Env }
else { "note: bash was not found, so tools/check-dist.sh was skipped" }
"$Env build in $Out : $((Get-ChildItem "$Out/public/previews").Count) thumbnails"
