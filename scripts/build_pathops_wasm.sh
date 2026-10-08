#!/usr/bin/env bash
# Stage 2b: build skia-pathops as a Pyodide wheel (wheel goes to dist/).
#  1. Skia (the sdist bundles the sources) is configured with its own `gn` for target_cpu="wasm"
#     using our emsdk and Pyodide's -fPIC/-fwasm-exceptions flags, and only `libskia.a` is built.
#  2. `pyodide build` compiles the Cython extension against it (BUILD_SKIA_FROM_SOURCE=0).
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/env.sh
activate_toolchain
JOBS="${JOBS:-$(nproc)}"
SRC="$REPO_ROOT/build/src/skia_pathops"
SKIA_OUT="$REPO_ROOT/build/skia-wasm"
rm -rf "$SRC"; mkdir -p "$SRC" "$REPO_ROOT/dist"
tar xf "$DOWNLOADS/skia_pathops-${SKIA_PATHOPS_VERSION}.tar.gz" -C "$SRC" --strip-components=1
if compgen -G "patches/skia-pathops/*.patch" >/dev/null; then
  for p in patches/skia-pathops/*.patch; do echo "patch skia-pathops: $p"; patch -d "$SRC" -p1 < "$p"; done
fi

SKIA_DIR="$SRC/src/cpp/skia-builder/skia"
GN="$SRC/src/cpp/skia-builder/bin/linux64/gn"      # gn binary shipped in the sdist (x86-64 Linux host)
EMSDK_ABS="$(cd "$EMSDK_DIR" && pwd)"
# same switches skia-pathops' own build_skia.py uses, plus target_cpu="wasm" and Pyodide's flags
ARGS='target_cpu="wasm" skia_emsdk_dir="'"$EMSDK_ABS"'" is_official_build=true is_debug=false
 skia_enable_pdf=false skia_enable_discrete_gpu=false skia_enable_ganesh=false skia_enable_skottie=false
 skia_enable_skshaper=false skia_use_dng_sdk=false skia_use_expat=false skia_use_freetype=false
 skia_use_fontconfig=false skia_use_gl=false skia_use_harfbuzz=false skia_use_icu=false
 skia_use_libjpeg_turbo_encode=false skia_use_libjpeg_turbo_decode=false skia_use_libpng_encode=false
 skia_use_libpng_decode=false skia_use_libwebp_encode=false skia_use_libwebp_decode=false skia_use_piex=false
 skia_use_xps=false skia_use_zlib=false skia_use_lua=false skia_use_wuffs=false skia_use_webgl=false
 skia_use_webgpu=false
 extra_cflags=["-fPIC","-fwasm-exceptions","-sSUPPORT_LONGJMP=wasm","-Oz","-DSK_DISABLE_LEGACY_PNG_WRITEBUFFER"]'
( cd "$SKIA_DIR" && "$GN" gen "$SKIA_OUT" --args="$(echo $ARGS)" )
ninja -C "$SKIA_OUT" -j "$JOBS" skia

# Defines that change Skia header layout/behaviour must match those used for libskia.a
export BUILD_SKIA_FROM_SOURCE=0 SKIA_LIBRARY_DIR="$SKIA_OUT"
export CPPFLAGS="-DNDEBUG -DSKNX_NO_SIMD -DSK_FORCE_8_BYTE_ALIGNMENT -DSK_DISABLE_TRACING"
( cd "$SRC" && pyodide build . --outdir "$REPO_ROOT/dist" )
