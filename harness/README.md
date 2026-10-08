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
