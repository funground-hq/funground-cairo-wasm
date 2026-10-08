# funground-cairo-wasm
WebAssembly (Pyodide) builds of pycairo, uharfbuzz and skia-pathops for funground

Spike S-134. Builds `pycairo 1.29.2` (static cairo 1.18.4 + pixman 0.46.4 + libpng 1.6.59 + zlib 1.3.1)
and `skia-pathops 0.9.2` (bundled Skia) as wheels for **Pyodide 314.0.7** (CPython 3.14.2, Emscripten 5.0.3,
wheel tag `pyemscripten_2026_0_wasm32`), and fetches the prebuilt `uharfbuzz` wheel. Design: `docs/architecture.md`, `docs/adr/`.

## Prerequisites
Linux x86-64 with bash, git, curl, cmake, make, pkg-config, patch, node 22 (smoke test) and either `uv` or Python 3.14.
Network: PyPI, GitHub, archive.ubuntu.com. 4 cores, ~6 GB disk. Every version/URL is in `scripts/versions.env`.

## Steps (run from the repo root, in this order)
| # | Command | What it does and why |
|---|---|---|
| 1 | `scripts/fetch_sources.sh` | Downloads the pinned tarballs to `downloads/` (override: `DOWNLOADS=dir`) and checks them against `sources.sha256`. Sources are exact, so builds are reproducible. |
| 2 | `scripts/setup_toolchain.sh` | Installs (idempotent): emsdk + Emscripten 5.0.3 (`build/emsdk`), a Python 3.14 venv `.venv314` with `pyodide-build==0.39.1` (+ meson, ninja, brotli), and the Pyodide **xbuildenv** from the release tarball. Prints all versions. Reuse existing installs with `EMSDK_DIR`, `VENV_DIR`, `PYODIDE_XBUILDENV_PATH`. |
| 3 | `scripts/build_wasm.sh` | Builds zlib, libpng, pixman, cairo into `build/wasm-prefix`, then the pycairo wheel into `dist/`. (`libs` / `wheel` argument builds half; `FORCE=1` rebuilds libs.) |
| 3b | `scripts/build_pathops_wasm.sh` | Builds Skia (`libskia.a`) with Skia's own gn/ninja for `target_cpu="wasm"`, then the skia-pathops wheel (needs `skia_pathops-0.9.2.tar.gz` in downloads). About 5 min. |
| 3c | `scripts/fetch_prebuilt_wheels.sh` | Downloads the prebuilt uharfbuzz wheel listed in `dist-sources.txt` (URL + sha256) into `dist/`. |
| 4 | `python3 -I scripts/check_wasm_imports.py dist/*.whl` and `scripts/wheel_sizes.sh` | Verifies that the side module imports nothing from cairo/pixman/png/zlib/Skia (only Python C-API, libc, libc++ and Emscripten runtime that Pyodide provides) and prints raw / gzip -9 / brotli -q 11 sizes. |
| 5 | `node test/node/smoke.mjs` | Loads Pyodide from `PYODIDE_DIST` (default `/home/user/pyodide-dist/pyodide`, the unpacked 314.0.7 release; fetch with `FETCH_DIST=1 scripts/fetch_sources.sh`), installs every wheel in `dist/` with micropip from the local file system, draws with pycairo (PNG round trip, PDF, SVG, PS, recording surface), shapes "Hello" with uharfbuzz, and unions two rectangles with pathops. |

### Run the tests in Node
`scripts/run_node_tests.sh` (see `harness/README.md`) renders the Session-1 and gallery goldens and runs the bench in Pyodide under Node,
for example `MODE=goldens OUT=results/pyodide scripts/run_node_tests.sh`. Results: `results/pyodide/SUMMARY.md`, `results/bench_comparison.md`.

Sandbox invocation used here: `EMSDK_DIR=/home/user/emsdk VENV_DIR=/home/user/venv314 PYODIDE_XBUILDENV_PATH=/home/user/xbuildenv DOWNLOADS=/home/user/dl scripts/<step>.sh`.

## Jargon
- **Side module**: a wasm shared library (`-sSIDE_MODULE=1`, here the `.so` in the wheel) loaded at runtime by the Pyodide main module, which supplies Python, libc and libc++.
- **xbuildenv**: Pyodide's cross-build environment (Python headers, config, cross files) that `pyodide build` compiles against.
- **-fPIC**: position-independent code; required for anything linked into a side module, including the static `.a` archives.
- **Wasm exceptions / SJLJ** (`-fwasm-exceptions -sSUPPORT_LONGJMP=wasm`): native wasm exception handling and setjmp/longjmp (libpng uses them). Must match the main module, so all flags come from `pyodide config get cflags`.
- **pyemscripten_2026_0**: the wheel platform tag for this Pyodide ABI.

## Build choices
- cross file `cross/emscripten-wasm32.cross.in` (rendered into `build/` with Pyodide's cflags minus the Python include dir; link flags without SIDE_MODULE so configure checks produce runnable Node programs).
- zlib: its `configure --static`; libpng: `emconfigure ./configure --disable-shared --with-pic`, no hardware optimizations.
- pixman: `-Ddefault_library=static -Dtests=disabled -Ddemos=disabled -Dgtk=disabled -Dlibpng=disabled -Dopenmp=disabled`. pixman 0.46.4 has no wasm SIMD path (options exist only for mmx/sse2/ssse3/vmx/arm-simd/neon/a64-neon/mips/loongson/rvv, none triggers for wasm32), so only the generic C paths are compiled; no SIMD option needed.
- cairo: `-Ddefault_library=static -Dfreetype=disabled -Dfontconfig=disabled -Dxlib=disabled -Dxcb=disabled -Dquartz=disabled -Ddwrite=disabled -Dglib=disabled -Dspectre=disabled -Dsymbol-lookup=disabled -Dtests=disabled -Dgtk_doc=false -Dpng=enabled -Dzlib=enabled -Dlzo=disabled` (tee left at auto = on). Surfaces: image, PNG, PDF, SVG, PS, recording, script, tee, observer. Threads: none; cairo is built with `CAIRO_NO_MUTEX` (no-op mutexes; see patch).
- pycairo: `pyodide build` from the sdist; `PKG_CONFIG_LIBDIR` points at `build/wasm-prefix/lib/pkgconfig`. `cairo.pc` has `Requires:` (not `Requires.private`) for zlib/libpng/pixman, so plain `pkg-config --libs` already links them statically.

## Patches (`patches/<lib>/`, applied by the build scripts)
| Patch | Why |
|---|---|
| `pixman/0001-emscripten-no-pthread.patch` | emcc accepts `-pthread`, so pixman found "threads" and put `-pthread -sPTHREAD_POOL_SIZE=4` into `pixman-1.pc`; that makes shared-memory wasm that cannot link into a Pyodide side module. |
| `cairo/0001-emscripten-no-pthread-no-mutex.patch` | Same problem in cairo's pthread probe; on emscripten skip it and define `CAIRO_NO_MUTEX=1` (Pyodide is single-threaded). |
| `cairo/0002-image-source-atomic-ptr-cast.patch` | Clang in Emscripten 5.0.3 turns passing `pixman_image_t **` to the C11 `_Atomic(void *) *` parameter into an error (gcc only warns). Explicit casts, no behaviour change. |

No patches were needed for libpng, zlib, pycairo or skia-pathops.

## Verified
Smoke test (`test/node/smoke.mjs`) passes on Node 22 with Pyodide 314.0.7: cairo 1.18.4 / pycairo 1.29.2, 64x64 ImageSurface sha256
`9b4b10e8024639559e60ef5bb9eae1efc8858a42c6575aa5c1cfc191481e11df`, uharfbuzz 0.56.3 shaping "Hello" with DejaVuSans (gids 43 72 79 79 82, identical to native uharfbuzz),
and pathops union of two rectangles (bounds 0,0,15,15; area 175). Not verified: GitHub Actions run, browsers other than Node, Linux arm64 hosts.
