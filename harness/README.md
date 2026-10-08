# harness

`fgrun.py` is the shared core: a pytest-free copy of funground's `tests/conftest.py` helpers
(`reset_funground`, `run_sketch`, `script_frame`: 30 frames at fps 1000, `f.run`/`f.show` patched, sketch
exec'd with `__name__ = "__sketch__"`), the gallery list loaded from `tools/make_gallery.py` as
`tests/test_gallery.py` does, and a per-sketch record of which C-extension modules are imported or used.
Standard library only, so it runs in CPython and in Pyodide.

`render_goldens.py --funground PATH --out DIR [--frames 30] [--gallery]` runs every Session-1 sketch that has
a golden (and, with `--gallery`, every deterministic gallery example that has one) headless and writes the final
frame as raw RGB (`DIR/<stem>.rgb`, `DIR/gallery/<id>.rgb`) plus `DIR/manifest.json` (size, sha256, seconds,
ok/error with traceback, modules imported, uharfbuzz/pathops calls made, versions). funground's modules are
purged before each sketch so the import list is per sketch. An error in one sketch is recorded and the run continues.
`main(argv)` is the entry point for a Node/Pyodide runner. `--pygame-platform` leaves `FUNGROUND_HEADLESS` unset,
as the Session-1 tests do (same bytes on the native build).

`compare.py --golden-dir tests/golden --a DIR [--b DIR] --out FILE.json [--diff-png DIR]` (native only: Pillow,
numpy) compares rendered directories with the golden PNGs, or with another rendered directory (wasm vs native).
Per image: byte identity, differing pixels (count, %), max and mean absolute channel difference, a histogram of the
per-pixel maximum difference (1, 2, 3-4, 5-8, 9-16, 17+), the share of differing pixels on anti-aliased edges
(3x3 neighbourhood of the reference not uniform, dilated by one pixel) and the bounding box. It prints a markdown
table and writes JSON; `--diff-png` writes amplified difference images.

`bench.py --funground PATH --out FILE [--top 10] [--frames 30] [--warmup 5]` counts the IR ops of the last frame
of every gallery example, ranks them, and times the heaviest: the renderer alone replaying the captured ops onto a
640x400 (density 1) and a 1280x800 (density 2, `attach(w, h, scale=2)`) surface, and the whole sketch loop
(draw + render) at density 1 and 2 using `FUNGROUND_BACKING_SCALE`. Median, mean, min, max over `--frames` repetitions
after `--warmup`. Runs in CPython and Pyodide.

`bench.py --peak-ids a,b` also replays the peak-op frame (most ops of the 30) of those examples, for sketches that redraw only on change and
have 0 ops in the last frame. `bench_table.py` turns a Node and a native `bench.json` into `results/bench_comparison.md`.

## Run the tests in Node
Plain Node 22, no npm install: `scripts/run_node_tests.sh` runs `test/node/run.mjs`, which loads Pyodide from `PYODIDE_DIST`
(the unpacked 314.0.7 release), loads fonttools, Pillow, numpy and pygame-ce from it, installs the wheels in `WHEELS` (default `dist/`) and the pure-Python
wheels in `PYWHEELS` (default `build/pywheels`: `pip download --only-binary :all: --no-deps -d build/pywheels svgelements==1.9.6 pypdf==6.19.0`, fetched by the
script if missing), mounts the funground checkout (`FUNGROUND`), this repository and `OUT` with NODEFS, prints the versions and calls
`render_goldens.main([... --gallery])` and/or `bench.main(...)`.

    MODE=goldens OUT=results/pyodide scripts/run_node_tests.sh                       # 13 + 78 goldens -> OUT/manifest.json, *.rgb
    MODE=bench BENCH_OUT=/out/bench.json BENCH_ARGS="--ids <ids> --peak-ids projects-05_typographic_portrait" \
        MIXER_STUB=1 OUT=results/pyodide scripts/run_node_tests.sh
    .venv-native/bin/python harness/compare.py --golden-dir <funground>/tests/golden --a results/pyodide --out results/pyodide/compare_vs_golden.json

`MIXER_STUB=1` replaces `pygame.mixer` (it cannot start in Pyodide) so sketches that make sounds can run headless; nothing is played.
Inside Pyodide the paths are `/funground`, `/repo`, `/out`; pass absolute `--out` paths. Bytecode writing is off, and the script checks that
`git status` of the funground checkout did not change.
