# Sourced by the other scripts (not run directly). Locations can be overridden from the
# environment; the defaults keep everything under the repo (build/, .venv314).
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$REPO_ROOT/scripts/versions.env"
export EMSDK_DIR="${EMSDK_DIR:-$REPO_ROOT/build/emsdk}"
export VENV_DIR="${VENV_DIR:-$REPO_ROOT/.venv314}"
export PYODIDE_XBUILDENV_PATH="${PYODIDE_XBUILDENV_PATH:-$REPO_ROOT/build/xbuildenv}"
export DOWNLOADS="${DOWNLOADS:-$REPO_ROOT/downloads}"
export PREFIX="${PREFIX:-$REPO_ROOT/build/wasm-prefix}"

activate_toolchain() {
  [ -f "$EMSDK_DIR/emsdk_env.sh" ] || { echo "ERROR: no emsdk at $EMSDK_DIR; run scripts/setup_toolchain.sh" >&2; return 1; }
  [ -x "$VENV_DIR/bin/activate" ] || [ -f "$VENV_DIR/bin/activate" ] || { echo "ERROR: no venv at $VENV_DIR; run scripts/setup_toolchain.sh" >&2; return 1; }
  # shellcheck disable=SC1091
  local keep="$EMSDK_DIR"   # emsdk_env.sh unsets EMSDK_DIR-like variables of its own
  source "$EMSDK_DIR/emsdk_env.sh" >/dev/null 2>&1
  export EMSDK_DIR="$keep"
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
}
