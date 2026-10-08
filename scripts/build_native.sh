#!/usr/bin/env bash
# Native (Linux, gcc) control build for spike S-134: the same tarballs and meson options as the
# wasm build, installed into build/native-prefix, then pycairo built from its sdist against it
# (cairo, pixman, libpng, zlib linked statically into _cairo*.so) in the venv .venv-native.
#
#   DOWNLOADS=dir  directory holding the tarballs (default: downloads/)
#   JOBS=n         parallel jobs (default: nproc)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=versions.env
source "$ROOT/scripts/versions.env"
DOWNLOADS="${DOWNLOADS:-$ROOT/downloads}"
JOBS="${JOBS:-$(nproc)}"
PREFIX="$ROOT/build/native-prefix"
WORK="$ROOT/build/native-work"
VENV="$ROOT/.venv-native"
export CFLAGS="-O2 -fPIC" CXXFLAGS="-O2 -fPIC"

# ---- 1. verify the sources against sources.sha256 -------------------------------------------
files=(
  "cairo_${CAIRO_VERSION}.orig.tar.xz"
  "pixman_${PIXMAN_VERSION}.orig.tar.gz"
  "libpng1.6_${LIBPNG_VERSION}.orig.tar.gz"
  "zlib_1.3.dfsg+really${ZLIB_VERSION}.orig.tar.gz"
  "pycairo-${PYCAIRO_VERSION}.tar.gz"
)
for f in "${files[@]}"; do
  [ -f "$DOWNLOADS/$f" ] || { echo "missing $DOWNLOADS/$f" >&2; exit 1; }
  want="$(grep -F "  $f" "$ROOT/sources.sha256" | cut -d' ' -f1)"
  have="$(sha256sum "$DOWNLOADS/$f" | cut -d' ' -f1)"
  [ -n "$want" ] && [ "$want" = "$have" ] || { echo "sha256 mismatch for $f" >&2; exit 1; }
  echo "ok  $f"
done

# ---- 2. venv with Python $PYTHON_VERSION and the build tools ---------------------------------
UV="$(command -v uv || echo /root/.local/bin/uv)"
if [ ! -x "$VENV/bin/python" ]; then
  "$UV" venv --python "$PYTHON_VERSION" "$VENV"
fi
PY="$VENV/bin/python"
"$UV" pip install --python "$PY" -q meson ninja meson-python pip setuptools wheel
export PATH="$VENV/bin:$PATH"          # meson/ninja from the venv (not installed system-wide)
command -v pkg-config >/dev/null || { echo "pkg-config is required" >&2; exit 1; }
command -v cmake >/dev/null || { echo "cmake is required (libpng)" >&2; exit 1; }

# ---- 3. C libraries ---------------------------------------------------------------------------
rm -rf "$WORK" "$PREFIX"; mkdir -p "$WORK" "$PREFIX"
unpack() { mkdir -p "$WORK/$1"; tar xf "$DOWNLOADS/$2" -C "$WORK/$1" --strip-components=1; }
unpack zlib   "zlib_1.3.dfsg+really${ZLIB_VERSION}.orig.tar.gz"
unpack libpng "libpng1.6_${LIBPNG_VERSION}.orig.tar.gz"
unpack pixman "pixman_${PIXMAN_VERSION}.orig.tar.gz"
unpack cairo  "cairo_${CAIRO_VERSION}.orig.tar.xz"
unpack pycairo "pycairo-${PYCAIRO_VERSION}.tar.gz"

export PKG_CONFIG_PATH="$PREFIX/lib/pkgconfig"
export PKG_CONFIG_LIBDIR="$PREFIX/lib/pkgconfig"   # ignore system cairo/pixman/png/zlib .pc files

echo "== zlib $ZLIB_VERSION"
( cd "$WORK/zlib" && ./configure --prefix="$PREFIX" --static && make -j"$JOBS" && make install )

echo "== libpng $LIBPNG_VERSION"
cmake -S "$WORK/libpng" -B "$WORK/libpng/_b" -G Ninja -DCMAKE_INSTALL_PREFIX="$PREFIX" \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_POSITION_INDEPENDENT_CODE=ON -DCMAKE_PREFIX_PATH="$PREFIX" \
  -DZLIB_ROOT="$PREFIX" -DZLIB_USE_STATIC_LIBS=ON \
  -DPNG_SHARED=OFF -DPNG_STATIC=ON -DPNG_TESTS=OFF -DPNG_TOOLS=OFF -DPNG_FRAMEWORK=OFF
cmake --build "$WORK/libpng/_b" -j"$JOBS" && cmake --install "$WORK/libpng/_b"

echo "== pixman $PIXMAN_VERSION"
meson setup "$WORK/pixman/_b" "$WORK/pixman" --prefix="$PREFIX" --libdir=lib --buildtype=release \
  -Db_staticpic=true -Ddefault_library=static -Dtests=disabled -Ddemos=disabled -Dgtk=disabled \
  -Dlibpng=disabled -Dopenmp=disabled
meson compile -C "$WORK/pixman/_b" -j "$JOBS" && meson install -C "$WORK/pixman/_b"

echo "== cairo $CAIRO_VERSION"
meson setup "$WORK/cairo/_b" "$WORK/cairo" --prefix="$PREFIX" --libdir=lib --buildtype=release \
  -Db_staticpic=true -Ddefault_library=static -Dfreetype=disabled -Dfontconfig=disabled \
  -Dxlib=disabled -Dxcb=disabled -Dquartz=disabled -Ddwrite=disabled -Dglib=disabled \
  -Dspectre=disabled -Dsymbol-lookup=disabled -Dtests=disabled -Dgtk_doc=false \
  -Dpng=enabled -Dzlib=enabled -Dlzo=disabled
meson compile -C "$WORK/cairo/_b" -j "$JOBS" && meson install -C "$WORK/cairo/_b"

# ---- 4. pycairo from the sdist, static link ----------------------------------------------------
# pycairo's meson asks pkg-config for cairo without --static, which would leave pixman/png/z
# unresolved against libcairo.a; this wrapper turns on --static semantics.
cat > "$WORK/pkg-config-static" <<WRAP
#!/bin/sh
exec "$(command -v pkg-config)" --static "\$@"
WRAP
chmod +x "$WORK/pkg-config-static"
echo "== pycairo $PYCAIRO_VERSION"
PKG_CONFIG="$WORK/pkg-config-static" "$UV" pip install --python "$PY" --no-build-isolation \
  --reinstall --no-cache "$WORK/pycairo"

# ---- 5. funground's other dependencies + compare.py's -----------------------------------------
"$UV" pip install --python "$PY" -q pygame-ce fonttools uharfbuzz skia-pathops svgelements pypdf pillow numpy

# ---- 6. report ---------------------------------------------------------------------------------
CAIRO_VERSION="$CAIRO_VERSION" "$PY" - <<'PYEOF'
import cairo, sys, glob, os, subprocess
print("python", sys.version.split()[0])
print("pycairo", cairo.version, "cairo", cairo.cairo_version_string())
so = glob.glob(os.path.join(os.path.dirname(cairo.__file__), "_cairo*.so"))[0]
out = subprocess.run(["ldd", so], capture_output=True, text=True).stdout
print(out)
bad = [l for l in out.splitlines() if "libcairo" in l or "libpixman" in l]
assert not bad, bad
assert cairo.cairo_version_string() == os.environ["CAIRO_VERSION"], cairo.cairo_version_string()
print("OK: statically linked cairo", cairo.cairo_version_string())
PYEOF
