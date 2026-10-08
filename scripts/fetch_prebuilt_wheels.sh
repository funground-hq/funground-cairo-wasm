#!/usr/bin/env bash
# Download the prebuilt wheels listed in dist-sources.txt into dist/ and verify their sha256.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p dist
grep -v '^#' dist-sources.txt | while read -r sha name url; do
  [ -n "$sha" ] || continue
  [ -s "dist/$name" ] || curl -fSL --retry 3 -o "dist/$name" "$url"
  echo "$sha  dist/$name" | sha256sum -c -
done
