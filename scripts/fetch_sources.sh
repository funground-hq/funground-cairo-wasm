#!/usr/bin/env bash
# Download every pinned tarball into ${DOWNLOADS:-downloads}/ (skipping files already
# present) and verify them against sources.sha256.
#   DOWNLOADS=/home/user/dl scripts/fetch_sources.sh   # reuse an existing download dir
#   FETCH_DIST=1 scripts/fetch_sources.sh              # also fetch the Pyodide distribution (for Node tests)
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/versions.env
DL="${DOWNLOADS:-downloads}"
mkdir -p "$DL"

urls=("$CAIRO_URL" "$PIXMAN_URL" "$LIBPNG_URL" "$ZLIB_URL" "$PYCAIRO_URL" "$XBUILDENV_URL" "$SKIA_PATHOPS_URL")
[ "${FETCH_DIST:-0}" = 1 ] && urls+=("$PYODIDE_DIST_URL")

for url in "${urls[@]}"; do
  name="$(basename "$url")"
  if [ -s "$DL/$name" ]; then
    echo "have  $name"
  else
    echo "fetch $name"
    curl -fSL --retry 3 -o "$DL/$name.part" "$url"
    mv "$DL/$name.part" "$DL/$name"
  fi
  # verify against sources.sha256 (first column hash, second column file name)
  want="$(awk -v n="$name" '$2==n {print $1}' sources.sha256)"
  [ -n "$want" ] || { echo "ERROR: $name missing from sources.sha256" >&2; exit 1; }
  got="$(sha256sum "$DL/$name" | awk '{print $1}')"
  if [ "$want" != "$got" ]; then
    echo "ERROR: sha256 mismatch for $name: want $want got $got" >&2
    exit 1
  fi
  echo "ok    $name"
done
