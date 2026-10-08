"""Op counts and frame times of the gallery examples (spike S-134).

    python harness/bench.py --funground PATH --out FILE [--top 10] [--frames N] [--warmup 5]
                            [--ids a,b] [--sizes 640x400,1280x800]

(i) Every example in examples/gallery (the list from tools/make_gallery.py, time-dependent ones
included) runs 30 headless frames; the IR ops of its last frame (``last_ops``, the frame after
warm-up) are counted and the examples ranked. (ii) For the ``--top`` heaviest, per frame time:

* replay: the captured ops of that last frame are replayed by a fresh ``CairoRenderer`` onto an
  ARGB32 surface of 640x400 (density 1) and 1280x800 (density 2, the HiDPI case: funground's
  ``attach(w, h, scale)`` with scale 2 puts a ``ctx.scale(2, 2)`` under the frame). An example whose canvas
  is not 640x400 is fitted uniformly (scale = min(640/w, 400/h) on top of the density), keeping its aspect.
  This is the cost of the renderer alone (cairo + pixman), without the sketch's Python.
* full frame: the whole sketch loop (draw() + render + present) at the example's own canvas size,
  at density 1 and at density 2 (FUNGROUND_BACKING_SCALE=2). Per frame draw() and _render() are
  timed separately and the loop iteration as a whole (headless ``tick``). A top-level script has no
  loop: its whole run is timed instead.

``--frames`` is the number of timed repetitions (default 30) after ``--warmup`` untimed ones.
random_seed(0) as in the tests. Runs in CPython and in Pyodide (``main(argv)``).
"""
from __future__ import annotations

import argparse
import gc
import json
import os
import statistics
import sys
import tempfile
from collections import Counter
from pathlib import Path

try:
    _HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _HERE = os.getcwd()
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import fgrun  # noqa: E402

TARGET_W, TARGET_H = 640, 400


def stats(samples_s):
    ms = sorted(s * 1000.0 for s in samples_s)
    if not ms:
        return None
    return {"n": len(ms), "median_ms": round(statistics.median(ms), 3), "mean_ms": round(statistics.fmean(ms), 3),
            "min_ms": round(ms[0], 3), "max_ms": round(ms[-1], 3),
            "stdev_ms": round(statistics.pstdev(ms), 3)}


def run_capture(path, frames=fgrun.FRAMES):
    """Run an example like the tests; return (size, ops of the last frame, active sketch)."""
    from funground import api

    fgrun.reset_funground()
    sketch = api.active_sketch()
    per_frame = []
    orig_render = sketch._render

    def counting_render():
        per_frame.append(len(sketch.last_ops or ()))
        orig_render()

    sketch._render = counting_render
    (w, h), data = fgrun.run_sketch(path, frames=frames)
    ops = tuple(sketch.last_ops or ())
    run_capture.per_frame = per_frame
    return (w, h), ops, data


def count_ops(path, gallery):
    entry = {"id": gallery.example_id(path), "time_dependent": bool(gallery.is_time_dependent(path))}
    scratch = tempfile.mkdtemp(prefix="fg-bench-")
    start = os.getcwd()
    os.chdir(scratch)
    try:
        size, ops, _ = run_capture(path)
        pf = run_capture.per_frame
        entry.update(status="ok", ops=len(ops), canvas=list(size), frames_drawn=len(pf),
                     ops_peak=max(pf) if pf else len(ops), ops_first=pf[0] if pf else len(ops),
                     ops_median=statistics.median(pf) if pf else len(ops))
        entry["op_types"] = dict(Counter(type(o).__name__ for o in ops).most_common(6))
    except BaseException as exc:                      # noqa: BLE001
        if isinstance(exc, KeyboardInterrupt):
            raise
        entry.update(status="error", ops=-1, error=f"{type(exc).__name__}: {exc}")
    finally:
        os.chdir(start)
        try:
            fgrun.end_test()
        except Exception:                             # noqa: BLE001
            pass
    return entry


def replay_times(ops, canvas, density, warmup, reps):
    """ms per frame of CairoRenderer replaying *ops* onto a 640x400 logical surface at *density*."""
    from funground import ir
    from funground.renderers.cairo2d import CairoRenderer

    w, h = canvas
    fit = min(TARGET_W / w, TARGET_H / h)
    renderer = CairoRenderer()
    renderer.attach(TARGET_W * density, TARGET_H * density, fit * density)
    frame = ir.Frame(list(ops))
    times = []
    gc.collect()
    for i in range(warmup + reps):
        t0 = fgrun.now()
        renderer.render(frame)
        renderer.surface.flush()
        dt = fgrun.now() - t0
        if i >= warmup:
            times.append(dt)
    result = stats(times)
    result.update(surface=[TARGET_W * density, TARGET_H * density], scale=round(fit * density, 5))
    pixels = renderer.pixels()
    result["_bgra"] = bytes(pixels.data)
    return result


def full_frame_times(path, density, warmup, reps):
    """Time the example's own loop at *density*; per frame: draw(), _render(), whole iteration."""
    from funground import api
    import funground

    prev = os.environ.get("FUNGROUND_BACKING_SCALE")
    if density != 1:
        os.environ["FUNGROUND_BACKING_SCALE"] = str(density)
    else:
        os.environ.pop("FUNGROUND_BACKING_SCALE", None)
    scratch = tempfile.mkdtemp(prefix="fg-bench-")
    start = os.getcwd()
    os.chdir(scratch)
    try:
        frames = warmup + reps
        fgrun.reset_funground()
        sketch = api.active_sketch()
        draw_t, render_t, tick_t = [], [], []
        platform = sketch._platform
        orig_tick, orig_render = platform.tick, sketch._render

        physical = []

        def timed_render():
            if not physical:
                surf = sketch._renderer.surface
                physical.append([surf.get_width(), surf.get_height()])
            t0 = fgrun.now()
            orig_render()
            render_t.append(fgrun.now() - t0)

        def timed_tick(fps):
            dt = orig_tick(fps)
            tick_t.append(dt)
            return dt

        sketch._render, platform.tick = timed_render, timed_tick

        source = Path(path).read_text(encoding="utf-8")
        namespace = {"__name__": "__sketch__", "__file__": str(path)}
        orig_run, orig_show = funground.run, funground.show

        def harness_run(*, fps=fgrun.FPS, max_frames=frames):
            import inspect
            caller = inspect.currentframe().f_back
            g = caller.f_globals
            draw = g.get("draw")
            if callable(draw):
                def timed_draw():
                    t0 = fgrun.now()
                    draw()
                    draw_t.append(fgrun.now() - t0)
                g["draw"] = timed_draw
            api.active_sketch().run_namespace(g, fps=fps, max_frames=max_frames)

        funground.run, funground.show = harness_run, (lambda: None)
        try:
            t_script = fgrun.now()
            exec(compile(source, str(path), "exec"), namespace)
            t_script = fgrun.now() - t_script
        finally:
            funground.run, funground.show = orig_run, orig_show

        if render_t or draw_t:
            result = {"mode": "loop", "frames_run": len(render_t),
                      "frame": stats(tick_t[warmup:][:reps]), "draw": stats(draw_t[warmup:][:reps]),
                      "render": stats(render_t[warmup:][:reps])}
            # frames in which the loop drew nothing (no_loop) have no render sample; say so
            if len(render_t) < frames:
                result["note"] = f"only {len(render_t)} frames were drawn of {frames} (no_loop / redraw)"
        else:
            result = {"mode": "script", "note": "no f.run(): whole script timed once; repeated below"}
        result["canvas_physical"] = physical[0] if physical else None
        return result, t_script
    finally:
        os.chdir(start)
        if prev is None:
            os.environ.pop("FUNGROUND_BACKING_SCALE", None)
        else:
            os.environ["FUNGROUND_BACKING_SCALE"] = prev
        try:
            fgrun.end_test()
        except Exception:                             # noqa: BLE001
            pass


def full_frame_script(path, density, reps):
    """Scripts: the whole run (exec + canvas flush) is the 'frame'."""
    prev = os.environ.get("FUNGROUND_BACKING_SCALE")
    if density != 1:
        os.environ["FUNGROUND_BACKING_SCALE"] = str(density)
    else:
        os.environ.pop("FUNGROUND_BACKING_SCALE", None)
    scratch = tempfile.mkdtemp(prefix="fg-bench-")
    start = os.getcwd()
    os.chdir(scratch)
    times = []
    try:
        for _ in range(reps + 1):
            fgrun.reset_funground()
            t0 = fgrun.now()
            fgrun.run_sketch(path)
            times.append(fgrun.now() - t0)
            fgrun.end_test()
    finally:
        os.chdir(start)
        if prev is None:
            os.environ.pop("FUNGROUND_BACKING_SCALE", None)
        else:
            os.environ["FUNGROUND_BACKING_SCALE"] = prev
    return {"mode": "script", "frame": stats(times[1:]), "note": "whole script run incl. 30-frame request ignored"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--funground", required=True)
    ap.add_argument("--out", required=True, help="JSON file")
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--frames", type=int, default=30, help="timed repetitions per measurement")
    ap.add_argument("--warmup", type=int, default=5)
    ap.add_argument("--ids", default="", help="comma-separated example ids to time instead of the top N")
    ap.add_argument("--count-only", action="store_true", help="only count ops")
    args = ap.parse_args(argv)

    fgrun.setup_environment(headless=True)
    root = fgrun.add_funground(args.funground)
    out = Path(args.out).resolve()
    import funground  # noqa: F401
    gallery = fgrun.gallery_tools(root)
    examples = gallery.examples()

    # ---- (i) op counts of every gallery example
    ranking = []
    for path in examples:
        e = count_ops(path, gallery)
        e["_path"] = str(path)
        ranking.append(e)
        print(f"{e['status']:5s} {e['id']:45s} ops={e['ops']:6d} canvas={e.get('canvas')}", flush=True)
    ranking.sort(key=lambda e: (-e["ops"], e["id"]))
    by_peak = sorted(ranking, key=lambda e: (-e.get("ops_peak", -1), e["id"]))

    doc = {"environment": fgrun.environment_info(),
           "config": {"timed_repetitions": args.frames, "warmup": args.warmup, "top": args.top,
                      "target_logical_canvas": [TARGET_W, TARGET_H], "frames_to_reach_ops": fgrun.FRAMES},
           "ranking": [{k: v for k, v in e.items() if k != "_path"} for e in ranking],
           "ranking_by_peak_ops": [[e["id"], e.get("ops_peak")] for e in by_peak[:20]],
           "ranking_note": "ops = IR ops of the last (30th) frame, the steady state after warm-up; ops_peak = most ops "
                           "in any of the 30 frames. A sketch that redraws only when something changed (dirty flag) "
                           "can have ops=0 in its last frame.", "top": []}
    paths = {e["id"]: e["_path"] for e in ranking}
    if args.ids:
        chosen = [i for i in args.ids.split(",") if i]
    else:
        chosen = [e["id"] for e in ranking if e["status"] == "ok"][:args.top]

    # ---- (ii) frame times of the heaviest
    for ident in ([] if args.count_only else chosen):
        path = Path(paths[ident])
        entry = next(e for e in ranking if e["id"] == ident)
        rec = {"id": ident, "ops": entry["ops"], "canvas": entry["canvas"], "op_types": entry.get("op_types"),
               "time_dependent": entry["time_dependent"]}
        scratch = tempfile.mkdtemp(prefix="fg-bench-")
        start = os.getcwd()
        os.chdir(scratch)
        try:
            size, ops, final = run_capture(path)
            rec["replay"] = {}
            for density in (1, 2):
                r = replay_times(ops, size, density, args.warmup, args.frames)
                bgra = r.pop("_bgra")
                if density == 1:
                    # does replaying the last frame's ops on a blank 640x400 surface reproduce the run's own
                    # last frame? (true when the sketch repaints its whole canvas every frame at 640x400)
                    rgb = bytes(b for i in range(0, len(bgra), 4) for b in (bgra[i + 2], bgra[i + 1], bgra[i]))
                    r["replay_equals_final_frame"] = (tuple(size) == (TARGET_W, TARGET_H) and rgb == final)
                rec["replay"][f"{TARGET_W * density}x{TARGET_H * density}"] = r
        except BaseException as exc:                  # noqa: BLE001
            if isinstance(exc, KeyboardInterrupt):
                raise
            rec["replay_error"] = f"{type(exc).__name__}: {exc}"
        finally:
            os.chdir(start)
            try:
                fgrun.end_test()
            except Exception:                         # noqa: BLE001
                pass
        rec["full_frame"] = {}
        for density in (1, 2):
            try:
                res, _ = full_frame_times(path, density, args.warmup, args.frames)
                if res["mode"] == "script":
                    res = full_frame_script(path, density, max(3, min(args.frames, 10)))
                rec["full_frame"][f"{density}x"] = res
            except BaseException as exc:              # noqa: BLE001
                if isinstance(exc, KeyboardInterrupt):
                    raise
                rec["full_frame"][f"{density}x"] = {"error": f"{type(exc).__name__}: {exc}"}
        doc["top"].append(rec)
        rp = rec.get("replay", {})
        print(f"timed {ident}: ops={rec['ops']} replay " +
              " ".join(f"{k}={v['median_ms']}ms" for k, v in rp.items()) + " full " +
              " ".join(f"{k}={v.get('frame', {}).get('median_ms') if isinstance(v.get('frame'), dict) else v.get('error')}ms"
                       for k, v in rec["full_frame"].items()), flush=True)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
