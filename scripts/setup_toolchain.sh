#!/usr/bin/env bash
# Install (idempotently) the three toolchain pieces and print their versions:
#   1. emsdk + Emscripten $EMSCRIPTEN_VERSION           -> $EMSDK_DIR   (default build/emsdk)
#   2. Python $PYTHON_VERSION venv with pyodide-build   -> $VENV_DIR    (default .venv314)
#   3. the Pyodide cross-build environment (xbuildenv)  -> $PYODIDE_XBUILDENV_PATH (default build/xbuildenv)
# Reuse an existing install by pointing the variables at it, e.g. in the sandbox:
#   EMSDK_DIR=/home/user/emsdk VENV_DIR=/home/user/venv314 PYODIDE_XBUILDENV_PATH=/home/user/xbuildenv \
#   DOWNLOADS=/home/user/dl scripts/setup_toolchain.sh
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/env.sh

# --- 1. emsdk -----------------------------------------------------------------
if [ ! -x "$EMSDK_DIR/emsdk" ]; then
  mkdir -p "$(dirname "$EMSDK_DIR")"
  git clone --depth 1 https://github.com/emscripten-core/emsdk.git "$EMSDK_DIR"
fi
if ! (source "$EMSDK_DIR/emsdk_env.sh" >/dev/null 2>&1 && emcc --version 2>/dev/null | head -1 | grep -q " $EMSCRIPTEN_VERSION "); then
  "$EMSDK_DIR/emsdk" install "$EMSCRIPTEN_VERSION"
  "$EMSDK_DIR/emsdk" activate "$EMSCRIPTEN_VERSION"
fi

# --- 2. host Python venv + pyodide-build ---------------------------------------
# The host Python must be $PYTHON_VERSION (Pyodide's). uv fetches it if the system has none;
# on a bare runner without uv or python$PYTHON_VERSION we bootstrap uv with pip.
if ! command -v uv >/dev/null && ! command -v "python$PYTHON_VERSION" >/dev/null; then
  python3 -m pip install --user uv
  export PATH="$HOME/.local/bin:$PATH"
fi
if [ ! -x "$VENV_DIR/bin/python" ]; then
  if command -v uv >/dev/null; then
    uv venv --python "$PYTHON_VERSION" "$VENV_DIR"
  else
    "python$PYTHON_VERSION" -m venv "$VENV_DIR"
  fi
fi
if ! "$VENV_DIR/bin/python" -c "import importlib.metadata as m,sys; sys.exit(m.version('pyodide-build')!='$PYODIDE_BUILD_VERSION')" 2>/dev/null; then
  if command -v uv >/dev/null; then
    uv pip install --python "$VENV_DIR/bin/python" "pyodide-build==$PYODIDE_BUILD_VERSION" brotli meson ninja
  else
    "$VENV_DIR/bin/python" -m pip install "pyodide-build==$PYODIDE_BUILD_VERSION" brotli meson ninja
  fi
fi
# extras used by build_wasm.sh / wheel_sizes.sh (meson+ninja drive pixman and cairo)
for mod in brotli meson ninja; do
  "$VENV_DIR/bin/python" -c "import $mod" 2>/dev/null || {
    if command -v uv >/dev/null; then uv pip install --python "$VENV_DIR/bin/python" "$mod"
    else "$VENV_DIR/bin/python" -m pip install "$mod"; fi; }
done

activate_toolchain

# --- 3. xbuildenv ----------------------------------------------------------------
want_py="$PYTHON_VERSION"
if ! (pyodide config get python_version 2>/dev/null | grep -q "^$want_py\." \
      && pyodide config get pyodide_abi_version 2>/dev/null | grep -q "^$PYODIDE_ABI$"); then
  xb="$DOWNLOADS/$(basename "$XBUILDENV_URL")"
  if [ -s "$xb" ]; then url="file://$(cd "$(dirname "$xb")" && pwd)/$(basename "$xb")"; else url="$XBUILDENV_URL"; fi
  pyodide xbuildenv install --url "$url"
fi

# --- report ----------------------------------------------------------------------
echo "================ toolchain versions ================"
echo "emcc:                 $(emcc --version | head -1)"
echo "python (host venv):   $(python --version)"
echo "pyodide-build:        $(python -c 'import importlib.metadata as m;print(m.version("pyodide-build"))')"
for k in emscripten_version python_version pyodide_abi_version; do
  echo "pyodide config $k: $(pyodide config get $k)"
done
