# Sprint 01 — stories (spike S-134)

Each box is an acceptance criterion. Ticked in the sprint review only with evidence in
`results/` or RESULTS.md.

### S-134.1 Toolchain
- [x] emsdk 5.0.3, host CPython 3.14, pyodide-build 0.39.1, xbuildenv 314.0.7 installed by `scripts/setup_toolchain.sh`, working with the blocked hosts above.
- [x] Exact versions printed by the script and recorded in RESULTS.md.

### S-134.2 The wasm build
- [x] `scripts/build_wasm.sh` builds zlib, libpng, pixman and cairo as static `-fPIC` archives into a prefix, with Pyodide's cflags.
- [x] cairo: image, PNG, PDF, SVG, PS and recording surfaces on; FreeType, fontconfig, X11, glib, threads off (or each one explained).
- [x] pycairo 1.29.2 wheel tagged `cp314-cp314-pyemscripten_2026_0_wasm32`, with no undefined cairo/pixman symbols.
- [x] Every patch in `patches/` with a one-line reason in the README.

### S-134.3 Native control and harness
- [x] `scripts/build_native.sh` builds the same sources natively and installs pycairo into a venv.
- [x] `harness/render_goldens.py` reproduces `tests/conftest.py::run_sketch` (30 frames) for every Session-1 sketch with a golden, in CPython and Pyodide alike.
- [x] `harness/compare.py`: byte-identical?, differing pixels, max and mean |Δ|, edge-only classification.
- [x] `harness/bench.py`: op counts of all gallery examples, the 10 heaviest, ms per frame at 640×400 and 1280×800.

### S-134.4 Pyodide in Node
- [x] `test/node/run.mjs` loads Pyodide 314.0.7 from a local distribution, installs the wheels and funground's pure-Python deps with micropip, runs the harness.
- [x] Three-way comparison results in `results/` (JPEG follow-up in `results/jpeg-check/`).

### S-134.5 Text
- [x] uharfbuzz in Pyodide: PyPI's wasm wheel imports and shapes, or a build (S-133).
- [x] skia-pathops: built, or the goldens that need it listed as skipped.

### S-134.6 Frame time
- [x] Node and native ms/frame for the 10 heaviest gallery examples at both sizes; ratio to native.

### S-134.7 Size
- [x] Each wheel raw, gzip -9 and brotli -q 11; total against 6 MB.

### S-134.8 CI
- [x] `.github/workflows/build.yml` runs the same scripts and uploads the wheel as an artifact.

### S-134.9 Results
- [x] RESULTS.md: versions, what built, pass/fail on (a)–(d), problems, patches, unverified items.
- [x] Sprint review written.
