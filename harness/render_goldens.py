"""Render funground's golden sketches to raw RGB files (spike S-134).

    python harness/render_goldens.py --funground PATH --out DIR [--frames 30] [--gallery]
                                     [--only SUBSTR] [--pygame-platform]

For every Session-1 sketch that has a golden (examples/session1/<stem>.py with
tests/golden/<stem>.png) this runs the sketch unchanged for 30 headless frames, exactly as
tests/test_examples_golden.py does, and writes the final frame's RGB bytes to ``DIR/<stem>.rgb``.
With --gallery the deterministic gallery examples that have a golden in tests/golden/gallery/
are written to ``DIR/gallery/<id>.rgb`` (run in a scratch working directory, as test_gallery.py does).
``DIR/manifest.json`` lists, per image: size, sha256, seconds, status (ok / error + traceback) and
the watched modules (cairo, uharfbuzz, pathops, pygame, PIL, ...) the sketch requested.

Runs in CPython and in Pyodide: call ``main(argv)`` or run the file with runpy. Errors in one
sketch are recorded and the run continues. Exit status is 0 even with sketch errors (see manifest).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

try:
    _HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:                                   # exec'd without __file__
    _HERE = os.getcwd()
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import fgrun  # noqa: E402


def _record(entry_id, kind, path, runner, out_file, frames, tracker, purge=True):
    """Run one sketch; return its manifest entry. The .rgb is written only on success."""
    entry = {"id": entry_id, "kind": kind, "source": str(path), "status": "ok"}
    t0 = fgrun.now()
    counters = None
    try:
        with tracker.active():
            if purge:
                fgrun.purge_funground()       # so the import list is per sketch, not "first user wins"
            fgrun.reset_funground()           # imports funground afresh, then a new Sketch (random_seed(0))
            counters = fgrun.install_usage_counters() if purge else None
            t0 = fgrun.now()                  # the time excludes importing funground itself
            (w, h), data = runner(path, frames=frames)
        entry["elapsed_s"] = round(fgrun.now() - t0, 4)
        entry.update(size=[w, h], bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                     file=str(out_file.name if kind == "session1" else f"gallery/{out_file.name}"))
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_bytes(data)
    except BaseException as exc:                    # noqa: BLE001 - a sketch may even call sys.exit
        if isinstance(exc, KeyboardInterrupt):
            raise
        entry["elapsed_s"] = round(fgrun.now() - t0, 4)
        entry["status"] = "error"
        entry["error"] = f"{type(exc).__name__}: {exc}"
        entry["traceback"] = fgrun.exception_text()
    entry["imports"] = sorted(tracker.seen)
    if counters is not None:
        entry["used"] = {k: dict(sorted(v.items())) for k, v in counters.items() if v}
    try:
        fgrun.end_test()
    except Exception as exc:                        # noqa: BLE001
        entry["teardown_error"] = repr(exc)
    return entry


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--funground", required=True, help="funground checkout (folder containing funground/)")
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--frames", type=int, default=fgrun.FRAMES)
    ap.add_argument("--gallery", action="store_true", help="also render the gallery goldens")
    ap.add_argument("--only", default="", help="only ids containing this text")
    ap.add_argument("--no-purge", action="store_true",
                    help="keep funground's modules loaded between sketches (imports are then credited to the first user)")
    ap.add_argument("--pygame-platform", action="store_true",
                    help="do not set FUNGROUND_HEADLESS (the Session-1 tests use the pygame dummy driver)")
    args = ap.parse_args(argv)

    fgrun.setup_environment(headless=not args.pygame_platform)
    root = fgrun.add_funground(args.funground)
    out = Path(args.out).resolve()                  # absolute: the run changes directory
    out.mkdir(parents=True, exist_ok=True)
    golden = root / "tests" / "golden"
    tracker = fgrun.ImportTracker()
    manifest = {"funground": str(root), "frames": args.frames, "entries": []}
    start_cwd = os.getcwd()

    import funground  # noqa: F401  (import cost is not part of any sketch's time)

    # ---- Session 1: every sketch with a golden (11_delta_time.py has none: it depends on the clock)
    os.chdir(root)                                   # pytest runs from the repository root
    try:
        for sketch in sorted((root / "examples" / "session1").glob("*.py")):
            if not (golden / f"{sketch.stem}.png").exists() or args.only not in sketch.stem:
                continue
            entry = _record(sketch.stem, "session1", sketch, fgrun.run_sketch,
                            out / f"{sketch.stem}.rgb", args.frames, tracker, not args.no_purge)
            manifest["entries"].append(entry)
            print(f"{entry['status']:5s} {entry['id']:28s} {entry.get('elapsed_s')}s {entry.get('imports')}", flush=True)
    finally:
        os.chdir(start_cwd)

    # ---- gallery: deterministic examples with a golden; each runs in a scratch directory
    if args.gallery:
        gallery = fgrun.gallery_tools(root)
        for path in gallery.examples():
            ident = gallery.example_id(path)
            if gallery.is_time_dependent(path) or not (golden / "gallery" / f"{ident}.png").exists():
                continue
            if args.only not in ident:
                continue
            scratch = tempfile.mkdtemp(prefix="fg-gallery-")
            os.chdir(scratch)
            try:
                entry = _record(ident, "gallery", path, fgrun.run_sketch,
                                out / "gallery" / f"{ident}.rgb", args.frames, tracker, not args.no_purge)
            finally:
                os.chdir(start_cwd)
            manifest["entries"].append(entry)
            print(f"{entry['status']:5s} gallery/{ident:40s} {entry.get('elapsed_s')}s {entry.get('imports')}", flush=True)

    manifest["environment"] = fgrun.environment_info()
    manifest["native_modules_loaded"] = fgrun.native_modules()
    manifest["funground_modules_loaded"] = fgrun.funground_modules()
    ok = sum(e["status"] == "ok" for e in manifest["entries"])
    manifest["summary"] = {"total": len(manifest["entries"]), "ok": ok, "error": len(manifest["entries"]) - ok}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"{ok}/{len(manifest['entries'])} rendered -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
