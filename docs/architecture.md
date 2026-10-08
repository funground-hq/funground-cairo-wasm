# Architecture: pycairo for Pyodide (spike S-134)

**Status:** spike, Sprint 01, from 8 October 2026. Question from funground's
`docs/design/Web_Target_Options.md` §3C and §6 row 2: can funground's Cairo renderer
(`funground/renderers/cairo2d.py`) run unchanged in the browser under Pyodide 314.0.7?

## What gets built

```
 Ubuntu archive (upstream orig tarballs, sha256-pinned)        PyPI sdist
   zlib 1.3.1   libpng 1.6.59   pixman 0.46.4   cairo 1.18.4   pycairo 1.29.2
       │             │               │               │               │
       └──── emcc 5.0.3, -fPIC -fwasm-exceptions -sSUPPORT_LONGJMP=wasm, static .a ───┐
                                                                                    ▼
                                     $PREFIX (wasm32 sysroot: lib/*.a, include, pkgconfig)
                                                                                    │
                       pyodide build (pyodide-build 0.39.1, xbuildenv 314.0.7, meson cross)
                                                                                    ▼
                         pycairo-1.29.2-cp314-cp314-pyemscripten_2026_0_wasm32.whl
                         (_cairo.so side module with cairo + pixman + libpng + zlib inside)
```

- **Static libraries, one side module.** cairo, pixman, libpng and zlib are linked into
  pycairo's `_cairo` extension. Nothing else in Pyodide needs them, so there is no shared
  library to load first.
- **Font backends off.** No FreeType, no fontconfig: funground turns text into paths with
  uharfbuzz + fontTools before it reaches Cairo. Surfaces on: image, PNG, PDF, SVG, PS, recording.
- **Same flags as Pyodide.** `-fwasm-exceptions -sSUPPORT_LONGJMP=wasm` must match Pyodide's
  own build (libpng uses `setjmp`/`longjmp`); taken from `pyodide config get cflags`.

## How it is tested

Three renderings of each golden are compared, to tell "wasm changed the pixels" apart from
"another cairo version or platform changed them":

```
  tests/golden/*.png  (Windows, pycairo 1.29.2 wheel = cairo 1.18.6)
          ▲ compare (b)
          │
  native Linux control ◄── compare ──► Pyodide 314.0.7 in Node
  (same sources and options,          (the wheel from this repo)
   built with gcc)
```

- `harness/` is plain Python that runs in both CPython and Pyodide. It re-implements
  funground's `tests/conftest.py::run_sketch` (30 frames, headless) without pytest, and writes
  raw RGB frames plus timings.
- `test/node/` starts Pyodide from the unpacked 314.0.7 distribution, installs the wheels with
  micropip from local files, mounts the funground checkout, and runs the harness.
- `harness/compare.py` reports byte identity, differing-pixel count, max/mean channel
  difference, and whether the differing pixels lie on anti-aliased edges.

## Repository layout

| Path | What |
|---|---|
| `scripts/versions.env` | Every pinned version and URL |
| `sources.sha256` | Hashes of every downloaded tarball |
| `scripts/` | Toolchain setup, wasm build, native control build, wheel sizes |
| `cross/`, `patches/` | Meson cross file and any source patches |
| `harness/` | Golden rendering, benchmark and comparison (Python, runs anywhere) |
| `test/node/` | Pyodide-in-Node runner |
| `results/` | Raw numbers from the runs that RESULTS.md cites |
| `docs/` | This note, ADRs, decision log, sprint documents |
