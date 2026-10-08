# ADR-001: Build route — pyodide-build with static cairo, pixman, libpng and zlib

**Status:** accepted for the spike (8 October 2026). **Decision:** CW-D-001.

## Context

The spike must produce a `pyemscripten_2026_0` wheel of pycairo for Pyodide 314.0.7. The brief
allows pyodide-build or cibuildwheel 4 (`platform = pyodide`). The sandbox's network blocks
`pyodide.github.io`, `cdn.jsdelivr.net`, `cairographics.org` and `gitlab.freedesktop.org`;
GitHub releases, PyPI, npm, the Ubuntu archive and the Emscripten release bucket are reachable.

## Options

- **A. `pyodide build` (pyodide-build 0.39.1) directly**, xbuildenv installed from the GitHub
  release tarball by URL, emsdk 5.0.3 installed with emsdk. Works offline once downloaded.
- **B. cibuildwheel 4, platform pyodide.** It wraps pyodide-build, and resolves the xbuildenv
  through `pyodide.github.io` metadata, which is blocked here.
- **C. A recipe in pyodide-recipes** (meta.yaml). Needs the Pyodide recipe tree; designed for
  Pyodide's own distribution, not for wheels we publish ourselves.

## Decision

A. The C libraries are built as static, position-independent archives with Emscripten's meson
cross file and the exact cflags Pyodide reports, then pycairo's meson-python build finds them
with pkg-config. CI (GitHub Actions, open network) runs the same scripts, so the recipe has one
route. cibuildwheel can wrap these scripts later (its `before-build` hook) when publishing to PyPI.

## Consequences

- The recipe is plain shell + meson; nothing depends on the blocked hosts.
- Moving to the next Pyodide (Python 3.15) means changing `scripts/versions.env` and rebuilding.
- Sources come from the Ubuntu archive (ADR-002).
