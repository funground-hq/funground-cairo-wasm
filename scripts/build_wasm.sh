#!/usr/bin/env bash
# Build zlib, libpng, pixman, cairo as static -fPIC wasm archives into build/wasm-prefix, then
# build the pycairo wheel against them with `pyodide build` into dist/.
#   scripts/build_wasm.sh            # everything (skips libraries already built; FORCE=1 rebuilds)
#   scripts/build_wasm.sh libs       # only the C libraries
#   scripts/build_wasm.sh wheel      # only the pycairo wheel
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/env.sh
activate_toolchain
WHAT="${1:-all}"
JOBS="${JOBS:-$(nproc)}"
BUILD="$REPO_ROOT/build"
SRC="$BUILD/src"
mkdir -p "$BUILD" "$SRC" "$PREFIX" "$REPO_ROOT/dist"

# Flags exactly as Pyodide builds its own extensions, minus the CPython include dir
# (the C libraries do not include Python.h) and minus -Oz/-O2 duplication.
PY_CFLAGS="$(pyodide config get cflags)"
CFLAGS_WASM="$(printf '%s' "$PY_CFLAGS" | tr ' ' '\n' | grep -v -e '^-I.*python' | tr '\n' ' ')"
LDFLAGS_WASM="-fwasm-exceptions -sSUPPORT_LONGJMP=wasm"
echo "CFLAGS  = $CFLAGS_WASM"
echo "LDFLAGS = $LDFLAGS_WASM"

# Emscripten ports (-sUSE_*) are not used; all libraries come from $PREFIX only.
export PKG_CONFIG_LIBDIR="$PREFIX/lib/pkgconfig"
export PKG_CONFIG_PATH="$PREFIX/lib/pkgconfig"
export PKG_CONFIG_SYSROOT_DIR=
export PKG_CONFIG_ALLOW_SYSTEM_CFLAGS=1
export PKG_CONFIG_ALLOW_SYSTEM_LIBS=1

unpack() { # name tarball -> $SRC/name (fresh), patches applied
  local name="$1" tarball="$2" dir="$SRC/$1"
  rm -rf "$dir"; mkdir -p "$dir"
  tar xf "$tarball" -C "$dir" --strip-components=1
  if compgen -G "patches/$name/*.patch" >/dev/null; then
    for p in patches/"$name"/*.patch; do
      echo "patch $name: $p"
      patch -d "$dir" -p1 < "$p"
    done
  fi
}
done_stamp() { [ -z "${FORCE:-}" ] && [ -f "$PREFIX/.stamp-$1" ]; }

render_cross() {
  local cf="$(printf '%s' "$CFLAGS_WASM" | awk '{for(i=1;i<=NF;i++) printf "%s'"'"'%s'"'"'", (i>1?", ":""), $i}')"
  local lf="$(printf '%s' "$LDFLAGS_WASM" | awk '{for(i=1;i<=NF;i++) printf "%s'"'"'%s'"'"'", (i>1?", ":""), $i}')"
  sed -e "s|@CFLAGS@|[$cf]|g" -e "s|@LDFLAGS@|[$lf]|g" cross/emscripten-wasm32.cross.in > "$BUILD/emscripten-wasm32.cross"
}

build_libs() {
  render_cross

  if ! done_stamp zlib; then
    unpack zlib "$DOWNLOADS/zlib_1.3.dfsg+really${ZLIB_VERSION}.orig.tar.gz"
    ( cd "$SRC/zlib"
      CC=emcc AR=emar RANLIB=emranlib CFLAGS="$CFLAGS_WASM" LDFLAGS="$LDFLAGS_WASM" \
        ./configure --static --prefix="$PREFIX"
      make -j"$JOBS" libz.a && make install )
    touch "$PREFIX/.stamp-zlib"
  fi

  if ! done_stamp libpng; then
    unpack libpng "$DOWNLOADS/libpng1.6_${LIBPNG_VERSION}.orig.tar.gz"
    ( cd "$SRC/libpng"
      emconfigure ./configure --host=wasm32-unknown-emscripten --prefix="$PREFIX" \
        --disable-shared --enable-static --with-pic --disable-tools \
        --enable-hardware-optimizations=no \
        CFLAGS="$CFLAGS_WASM" CPPFLAGS="-I$PREFIX/include" LDFLAGS="$LDFLAGS_WASM -L$PREFIX/lib"
      emmake make -j"$JOBS" && emmake make install )
    touch "$PREFIX/.stamp-libpng"
  fi

  if ! done_stamp pixman; then
    unpack pixman "$DOWNLOADS/pixman_${PIXMAN_VERSION}.orig.tar.gz"
    ( cd "$SRC/pixman"
      meson setup _b --cross-file "$BUILD/emscripten-wasm32.cross" --prefix "$PREFIX" --libdir lib \
        --buildtype release -Ddefault_library=static -Db_staticpic=true \
        -Dtests=disabled -Ddemos=disabled -Dgtk=disabled -Dlibpng=disabled -Dopenmp=disabled
      meson compile -C _b -j "$JOBS" && meson install -C _b )
    touch "$PREFIX/.stamp-pixman"
  fi

  if ! done_stamp cairo; then
    unpack cairo "$DOWNLOADS/cairo_${CAIRO_VERSION}.orig.tar.xz"
    ( cd "$SRC/cairo"
      meson setup _b --cross-file "$BUILD/emscripten-wasm32.cross" --prefix "$PREFIX" --libdir lib \
        --buildtype release -Ddefault_library=static -Db_staticpic=true --wrap-mode=nofallback \
        -Dfreetype=disabled -Dfontconfig=disabled -Dxlib=disabled -Dxcb=disabled -Dquartz=disabled \
        -Ddwrite=disabled -Dglib=disabled -Dspectre=disabled -Dsymbol-lookup=disabled \
        -Dtests=disabled -Dgtk_doc=false -Dpng=enabled -Dzlib=enabled -Dlzo=disabled
      meson compile -C _b -j "$JOBS" && meson install -C _b )
    touch "$PREFIX/.stamp-cairo"
  fi
}

build_wheel() {
  local sdist="$DOWNLOADS/pycairo-${PYCAIRO_VERSION}.tar.gz"
  rm -rf "$SRC/pycairo"; mkdir -p "$SRC/pycairo"
  tar xf "$sdist" -C "$SRC/pycairo" --strip-components=1
  ( cd "$SRC/pycairo"
    # pyodide build injects Pyodide's cross file, cflags and ldflags; we add only the pkg-config
    # environment so that `dependency('cairo')` resolves to our static prefix.
    pyodide build . --outdir "$REPO_ROOT/dist" )
}

case "$WHAT" in
  libs)  build_libs ;;
  wheel) build_wheel ;;
  all)   build_libs; build_wheel ;;
  *) echo "usage: $0 [all|libs|wheel]" >&2; exit 2 ;;
esac
