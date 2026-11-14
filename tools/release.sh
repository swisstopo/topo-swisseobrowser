#!/usr/bin/env bash
# Creates the GitHub release of a production deploy (deploy-prod.yml, job "release"; README, Releases).
#
# Version: semver tags vMAJOR.MINOR.PATCH on origin. The first release is v1.0.0; after that every merge of int
# into main is a minor release, unless its pull request carries one of the labels
#   release: patch   fixes only
#   release: major   a break: links or URL parameters that no longer work, a function removed
#   release: none    no release
# Notes: the pull request, then one line per commit since the previous release (Dependabot updates apart).
#
# The previous version is read from origin, never from local tags: a clone that also fetched the upstream
# Copernicus Browser holds its tags v1.10.4 ... v1.58.0, which are not ours.
#
#   bash tools/release.sh             what the workflow runs (needs GH_TOKEN with contents: write)
#   bash tools/release.sh --dry-run   prints the version and the notes, creates nothing
# For a dry run, RELEASE_LABELS, PR_NUMBER and PR_TITLE stand in for the pull request (and are looked up with gh
# when it is installed and they are not set); RELEASE_PREV pretends a previous version, e.g. v1.0.0.
set -euo pipefail

DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1
SHA=$(git rev-parse "${GITHUB_SHA:-HEAD}")
REPO=${GITHUB_REPOSITORY:-$(git remote get-url origin | sed -E 's#^(https://github\.com/|git@github\.com:)##; s#\.git$##')}
PROD=https://swisseobrowser.swisstopo.admin.ch
FIRST=afe553e      # "Merge the initial commit of swisstopo/topo-swisseobrowser": where our own history begins

# the release tags on origin: "sha refs/tags/vX.Y.Z" (an annotated tag also lists its commit as ...^{})
tags=$(git ls-remote --tags origin 'v*' | sed -nE 's#^([0-9a-f]+)[[:space:]]+refs/tags/(v[0-9]+\.[0-9]+\.[0-9]+)(\^\{\})?$#\1 \2#p')
if printf '%s\n' "$tags" | grep -q "^$SHA "; then
  echo "$SHA already has the release $(printf '%s\n' "$tags" | grep "^$SHA " | head -1 | cut -d' ' -f2): nothing to do"
  exit 0
fi
prev=${RELEASE_PREV:-$(printf '%s\n' "$tags" | awk 'NF {print $2}' | sort -uV | tail -1)}
prevsha=""
if [ -n "$prev" ]; then
  prevsha=$(printf '%s\n' "$tags" | awk -v t="$prev" '$2 == t {print $1}' | tail -1)
  [ -n "$prevsha" ] || prevsha=$(git rev-parse --verify -q "$prev^{commit}" || true)
  [ -n "$prevsha" ] || prevsha=$FIRST      # RELEASE_PREV in a dry run: a version that is not tagged
fi

# the pull request this commit merged, and its labels
if [ -z "${RELEASE_LABELS+x}${PR_NUMBER+x}" ] && command -v gh >/dev/null; then
  pr=$(gh api "repos/$REPO/commits/$SHA/pulls" --jq '.[0] // empty | [.number, .title, ([.labels[].name] | join(","))] | @tsv' || true)
  PR_NUMBER=$(printf '%s' "$pr" | cut -f1); PR_TITLE=$(printf '%s' "$pr" | cut -f2); RELEASE_LABELS=$(printf '%s' "$pr" | cut -f3)
fi
labels=",${RELEASE_LABELS:-},"
case "$labels" in *",release: none,"*) echo "label 'release: none': no release"; exit 0;; esac

if [ -z "$prev" ]; then
  next=v1.0.0
else
  IFS=. read -r MA MI PA <<< "${prev#v}"
  case "$labels" in
    *",release: major,"*) next="v$((MA + 1)).0.0" ;;
    *",release: patch,"*) next="v$MA.$MI.$((PA + 1))" ;;
    *)                    next="v$MA.$((MI + 1)).0" ;;
  esac
fi

notes=$(mktemp)
{
  if [ -n "${PR_NUMBER:-}" ]; then echo "${PR_TITLE:-Merge of int into main} (#$PR_NUMBER)"; echo; fi
  if [ -z "$prev" ]; then
    echo "The first versioned release of the swissEO Browser in production. It contains everything since the"
    echo "repository began:"
    echo
  fi
  range="${prevsha:-$FIRST}..$SHA"
  own=$(git log --no-merges --reverse --format='%an%x09- %s (%h)' "$range" | grep -v '^dependabot' | cut -f2- || true)
  deps=$(git log --no-merges --reverse --format='%an%x09- %s (%h)' "$range" | grep '^dependabot' | cut -f2- || true)
  echo "### Changes"; echo
  if [ -n "$own" ]; then echo "$own"; else echo "- no changes of our own (see below)"; fi
  if [ -n "$deps" ]; then echo; echo "### Dependencies"; echo; echo "$deps"; fi
  echo
  echo "Production: $PROD"
  if [ -n "$prev" ]; then echo "Full changelog: https://github.com/$REPO/compare/$prev...$next"; fi
} > "$notes"

echo "release $next (previous: ${prev:-none}; labels: ${RELEASE_LABELS:-none}) for $SHA"
if [ "$DRY" = 1 ]; then echo "----- notes (dry run, nothing created) -----"; cat "$notes"; exit 0; fi
gh release create "$next" --repo "$REPO" --target "$SHA" --title "swissEO Browser $next" --notes-file "$notes" --latest
echo "created https://github.com/$REPO/releases/tag/$next"
