"""Build results/bench_comparison.md from the Node and native bench JSON files (standard library only).

    python harness/bench_table.py --node results/pyodide/bench.json --native results/native/bench_rerun.json \
        --out results/bench_comparison.md [--cpu "..."] [--node-version "..."]
"""
import argparse
import json
import statistics


def med(rec, *keys):
    for k in keys:
        if not isinstance(rec, dict) or k not in rec:
            return None
        rec = rec[k]
    return rec.get("median_ms") if isinstance(rec, dict) else None


def fmt(x):
    return "n/a" if x is None else f"{x:.1f}" if x >= 10 else f"{x:.2f}"


def ratio(a, b):
    return None if a is None or b is None or b == 0 else a / b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--node", required=True)
    ap.add_argument("--native", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cpu", default="")
    ap.add_argument("--versions", default="")
    ap.add_argument("--threshold", type=float, default=12.0)
    a = ap.parse_args()
    node, nat = json.load(open(a.node)), json.load(open(a.native))
    nt = {t["id"]: t for t in node["top"]}
    vt = {t["id"]: t for t in nat["top"]}
    ids = [t["id"] for t in nat["top"]]
    cols = [("replay 640x400", ("replay", "640x400")), ("replay 1280x800", ("replay", "1280x800")),
            ("full frame 1x", ("full_frame", "1x", "frame")), ("full frame 2x", ("full_frame", "2x", "frame"))]
    L = []
    L.append("# Bench comparison: Pyodide 314.0.7 in Node vs native CPython (same sources)\n")
    L.append(f"{a.versions}\n" if a.versions else "")
    L.append(f"CPU: {a.cpu}. Medians in ms over {node['config']['timed_repetitions']} timed repetitions after "
             f"{node['config']['warmup']} warm-up. Ratio = Node / native. Node: `{a.node}`; native: `{a.native}` "
             "(run right after the Node run, same settings, same 10 examples).\n")
    L.append("## Per example (ms, median)\n")
    head = "| example | ops | " + " | ".join(f"{c} Node | native | x" for c, _ in cols) + " |"
    L.append(head)
    L.append("|---|---:|" + "---:|---:|---:|" * len(cols))
    ratios = {c: [] for c, _ in cols}
    stats = {c: ([], []) for c, _ in cols}
    for i in ids:
        row = [f"{i}", str(vt[i]["ops"])]
        for c, k in cols:
            n, v = med(nt.get(i, {}), *k), med(vt[i], *k)
            r = ratio(n, v)
            if r is not None:
                ratios[c].append(r)
            if n is not None: stats[c][0].append(n)
            if v is not None: stats[c][1].append(v)
            row += [fmt(n), fmt(v), "n/a" if r is None else f"{r:.2f}"]
        L.append("| " + " | ".join(row) + " |")
    row = ["**mean of the 10**", ""]
    for c, _ in cols:
        mn, mv = (statistics.fmean(s) if s else None for s in stats[c])
        row += [fmt(mn), fmt(mv), f"{statistics.fmean(ratios[c]):.2f} (of ratios) / {mn / mv:.2f} (of means)"]
    L.append("| " + " | ".join(row) + " |")
    L.append("")
    T = a.threshold
    def count(d, key):
        return sum(1 for i in ids if (med(d.get(i, {}), *key) or 1e9) <= T)
    L.append(f"## Examples at or under {T:g} ms\n")
    L.append("| measure | Node | native |\n|---|---:|---:|")
    L.append(f"| replay @1280x800 | {count(nt, cols[1][1])} / 10 | {count(vt, cols[1][1])} / 10 |")
    L.append(f"| replay @640x400 | {count(nt, cols[0][1])} / 10 | {count(vt, cols[0][1])} / 10 |")
    L.append(f"| full frame 2x (draw + render + loop) | {count(nt, cols[3][1])} / 10 | {count(vt, cols[3][1])} / 10 |")
    L.append(f"| full frame 1x | {count(nt, cols[2][1])} / 10 | {count(vt, cols[2][1])} / 10 |")
    L.append("")
    L.append("## Full frame split at 2x (ms, median): draw() / render\n")
    L.append("| example | Node draw | Node render | native draw | native render |\n|---|---:|---:|---:|---:|")
    for i in ids:
        L.append(f"| {i} | {fmt(med(nt.get(i, {}), 'full_frame', '2x', 'draw'))} | {fmt(med(nt.get(i, {}), 'full_frame', '2x', 'render'))} | "
                 f"{fmt(med(vt[i], 'full_frame', '2x', 'draw'))} | {fmt(med(vt[i], 'full_frame', '2x', 'render'))} |")
    L.append("")
    L.append("## Supplement: redraw-on-change examples (0 ops in the last frame)\n")
    L.append("projects-01, projects-05 (1377 ops at its peak frame) and saving-04 draw only when something changed, so "
             "the last frame is empty and they rank last by last-frame ops. The peak-op frame of projects-05 replayed:\n")
    L.append("| example | peak ops | size | Node | native | x |\n|---|---:|---|---:|---:|---:|")
    np_, vp_ = ({r["id"]: r for r in d.get("peak_replay", [])} for d in (node, nat))
    for i in vp_:
        for s in ("640x400", "1280x800"):
            n, v = med(np_.get(i, {}), "replay", s), med(vp_[i], "replay", s)
            L.append(f"| {i} | {vp_[i].get('ops')} | {s} | {fmt(n)} | {fmt(v)} | {'n/a' if ratio(n, v) is None else f'{ratio(n, v):.2f}'} |")
    L.append("")
    L.append("## Notes\n")
    L.append("- studios-03_rhythm and studios-05_text_as_geometry are top-level scripts (no `f.run()` loop): their "
             "\"full frame\" columns are the time of the whole script run (draw + canvas flush), not one frame; no draw/render split.")
    L.append("- \"full frame\" is the headless loop iteration (draw() + render + present), median; the ratio columns are Node / native.")
    L.append("- Replay times the renderer alone (cairo + pixman); full frame adds funground's Python (draw, IR building, text shaping), "
             "so its ratio mostly reflects Pyodide's CPython speed versus native.")
    L.append("")
    open(a.out, "w").write("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
