#!/usr/bin/env bash
# Print raw, gzip -9 and brotli -q 11 sizes (bytes) of every wheel in dist/ (or given paths).
# brotli: uses the `brotli` CLI if present, otherwise the Python `brotli` module from the venv.
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/env.sh
[ -f "$VENV_DIR/bin/activate" ] && source "$VENV_DIR/bin/activate"
files=("$@"); [ ${#files[@]} -gt 0 ] || files=(dist/*.whl)
br() {
  if command -v brotli >/dev/null; then brotli -q 11 -c "$1" | wc -c
  else python -c 'import sys,brotli;print(len(brotli.compress(open(sys.argv[1],"rb").read(),quality=11)))' "$1"; fi
}
printf '%-72s %10s %10s %10s\n' wheel raw gzip-9 brotli-11
for f in "${files[@]}"; do
  printf '%-72s %10d %10d %10d\n' "$(basename "$f")" "$(wc -c < "$f")" "$(gzip -9 -c "$f" | wc -c)" "$(br "$f")"
done

# A wheel is a deflate-compressed zip, so gzip/brotli of the wheel gain nothing. What a CDN that
# serves wheels with Content-Encoding can do better is brotli over the *uncompressed* wasm payload:
echo
printf '%-72s %10s %10s %10s\n' "wasm members (uncompressed)" raw gzip-9 brotli-11
for f in "${files[@]}"; do
  python - "$f" <<'PY'
import sys, zipfile, gzip, brotli, os
with zipfile.ZipFile(sys.argv[1]) as z:
    for n in z.namelist():
        if n.endswith(".so"):
            d = z.read(n)
            print(f"{os.path.basename(sys.argv[1])[:20]+':'+os.path.basename(n):<72} {len(d):>10} {len(gzip.compress(d,9)):>10} {len(brotli.compress(d,quality=11)):>10}")
PY
done
