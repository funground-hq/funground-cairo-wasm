#!/usr/bin/env bash
# Run the harness in Pyodide under Node. See test/node/run.mjs for the variables.
#   MODE=goldens|bench|all  OUT=results/pyodide  scripts/run_node_tests.sh
set -euo pipefail
cd "$(dirname "$0")/.."
export PYODIDE_DIST="${PYODIDE_DIST:-/home/user/pyodide-dist/pyodide}"
export FUNGROUND="${FUNGROUND:-/home/user/funground-hq/funground}"
export WHEELS="${WHEELS:-dist}" PYWHEELS="${PYWHEELS:-build/pywheels}" OUT="${OUT:-results/pyodide}" MODE="${MODE:-all}"
if [ ! -d "$PYWHEELS" ] || [ -z "$(ls "$PYWHEELS" 2>/dev/null)" ]; then
  echo "fetching pure-Python wheels into $PYWHEELS (needs pip + network)"
  pip download --only-binary :all: --no-deps -d "$PYWHEELS" svgelements==1.9.6 pypdf==6.19.0
fi
before=$(git -C "$FUNGROUND" status --porcelain 2>/dev/null || true)
node test/node/run.mjs "$@"
after=$(git -C "$FUNGROUND" status --porcelain 2>/dev/null || true)
[ "$before" = "$after" ] || { echo "WARNING: the funground checkout changed during the run" >&2; exit 2; }
