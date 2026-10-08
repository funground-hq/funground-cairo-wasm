"""Compare rendered frames with the golden PNGs, or with another rendered directory (native only).

    python harness/compare.py --golden-dir tests/golden --a results/native --out results/native/compare_vs_golden.json
    python harness/compare.py --a results/wasm --b results/native --out results/wasm_vs_native.json [--diff-png DIR]

``--a`` / ``--b`` are directories written by render_goldens.py (``<id>.rgb`` and ``gallery/<id>.rgb``,
sizes from manifest.json). Without ``--b`` each image in A is compared with
``--golden-dir/<id>.png`` (gallery images in ``--golden-dir/gallery/``); with ``--b`` A is compared with B.
Per image it reports: byte-identical, differing pixels (count, %), max and mean |difference| per channel
over the differing pixels, a histogram of each differing pixel's largest channel difference (1, 2, 3-4,
5-8, 9-16, 17+), the share of differing pixels on an anti-aliased edge (a pixel whose 3x3 neighbourhood
in the reference is not uniform, dilated by one pixel) and the bounding box of the differences.
Prints a markdown table and writes JSON. Needs Pillow and numpy; not meant for Pyodide.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

BUCKETS = [("1", 1, 1), ("2", 2, 2), ("3-4", 3, 4), ("5-8", 5, 8), ("9-16", 9, 16), ("17+", 17, 255)]


def edge_mask(ref: np.ndarray) -> np.ndarray:
    """True where the 3x3 neighbourhood of the reference is not uniform, dilated by one pixel."""
    h, w, _ = ref.shape
    pad = np.pad(ref, ((1, 1), (1, 1), (0, 0)), mode="edge")
    nonuniform = np.zeros((h, w), dtype=bool)
    for dy in range(3):
        for dx in range(3):
            nonuniform |= (pad[dy:dy + h, dx:dx + w] != ref).any(axis=2)
    pad = np.pad(nonuniform, 1, mode="constant")
    dilated = np.zeros((h, w), dtype=bool)
    for dy in range(3):
        for dx in range(3):
            dilated |= pad[dy:dy + h, dx:dx + w]
    return dilated


def compare_arrays(a: np.ndarray, ref: np.ndarray) -> dict:
    """a, ref: uint8 arrays (h, w, 3). Statistics of a against ref."""
    h, w, _ = ref.shape
    diff = np.abs(a.astype(np.int16) - ref.astype(np.int16))
    pix = diff.max(axis=2)                       # per-pixel largest channel difference
    differing = pix > 0
    n = int(differing.sum())
    out = {"width": w, "height": h, "pixels": h * w, "byte_identical": n == 0, "diff_pixels": n,
           "diff_pixels_pct": round(100.0 * n / (h * w), 5)}
    if n == 0:
        out.update(max_abs_diff=0, mean_abs_diff=0.0, histogram={k: 0 for k, _, _ in BUCKETS},
                   edge_only=True, share_in_edge_mask=None, bbox=None, diff_channel_values=0)
        return out
    vals = diff[differing]                       # (n, 3)
    out["max_abs_diff"] = int(vals.max())
    out["mean_abs_diff"] = round(float(vals.mean()), 4)             # over all 3 channels of differing pixels
    out["mean_max_channel_diff"] = round(float(pix[differing].mean()), 4)
    out["diff_channel_values"] = int((vals > 0).sum())
    out["histogram"] = {k: int(((pix >= lo) & (pix <= hi)).sum()) for k, lo, hi in BUCKETS}
    edges = edge_mask(ref)
    inside = int((differing & edges).sum())
    out["share_in_edge_mask"] = round(inside / n, 5)
    out["edge_only"] = inside == n
    ys, xs = np.nonzero(differing)
    out["bbox"] = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]   # x0, y0, x1, y1 inclusive
    out["edge_mask_pct_of_image"] = round(100.0 * edges.mean(), 3)
    return out


def load_dir(path: Path) -> dict:
    """{id: (size, loader)} for a render_goldens.py output directory."""
    manifest = {}
    mf = path / "manifest.json"
    if mf.exists():
        for e in json.loads(mf.read_text(encoding="utf-8"))["entries"]:
            if e.get("status") == "ok":
                manifest[e["id"] + ("" if e["kind"] == "session1" else "@gallery")] = e
    items = {}
    for f in sorted(path.glob("*.rgb")) + sorted((path / "gallery").glob("*.rgb")):
        gallery = f.parent.name == "gallery"
        key = f.stem + ("@gallery" if gallery else "")
        size = tuple(manifest[key]["size"]) if key in manifest else None
        items[key] = (size, f)
    return items


def read_rgb(file: Path, size, hint) -> np.ndarray:
    data = np.frombuffer(file.read_bytes(), dtype=np.uint8)
    if size is None:
        size = hint
    if size is None or data.size != size[0] * size[1] * 3:
        raise ValueError(f"cannot work out the size of {file} ({data.size} bytes, size {size})")
    return data.reshape(size[1], size[0], 3)


def read_png(file: Path) -> np.ndarray:
    return np.asarray(Image.open(file).convert("RGB"))


def save_diff(a: np.ndarray, ref: np.ndarray, target: Path, gain: int = 32) -> None:
    diff = np.abs(a.astype(np.int16) - ref.astype(np.int16)).max(axis=2)
    img = np.zeros(ref.shape, dtype=np.uint8)
    img[...] = (ref.astype(np.float32) * 0.25).astype(np.uint8)           # dim reference for context
    amp = np.clip(diff.astype(np.int32) * gain, 0, 255).astype(np.uint8)
    img[diff > 0] = np.stack([np.maximum(amp, 80)[diff > 0], np.zeros_like(amp)[diff > 0],
                              np.zeros_like(amp)[diff > 0]], axis=1)
    target.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(img).save(target)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--golden-dir", help="folder with <stem>.png and gallery/<id>.png (needed without --b)")
    ap.add_argument("--a", required=True, help="rendered directory to judge")
    ap.add_argument("--b", help="rendered directory used as the reference instead of the goldens")
    ap.add_argument("--out", required=True, help="JSON file to write")
    ap.add_argument("--diff-png", help="write amplified difference PNGs for differing images here")
    args = ap.parse_args(argv)
    if not args.b and not args.golden_dir:
        ap.error("give --golden-dir, or --b")

    A = load_dir(Path(args.a))
    B = load_dir(Path(args.b)) if args.b else None
    ref_name = args.b if args.b else args.golden_dir
    results, missing = {}, []
    for key, (size, file) in A.items():
        ident, gallery = (key[:-8], True) if key.endswith("@gallery") else (key, False)
        label = ("gallery/" if gallery else "") + ident
        try:
            if B is not None:
                if key not in B:
                    missing.append(label)
                    continue
                bsize, bfile = B[key]
                ref = read_rgb(bfile, bsize, size)
            else:
                png = Path(args.golden_dir) / ("gallery" if gallery else "") / f"{ident}.png"
                if not png.exists():
                    missing.append(label)
                    continue
                ref = read_png(png)
            a = read_rgb(file, size, (ref.shape[1], ref.shape[0]))
            if a.shape != ref.shape:
                results[label] = {"error": f"size differs: {a.shape[1]}x{a.shape[0]} vs {ref.shape[1]}x{ref.shape[0]}"}
                continue
            res = compare_arrays(a, ref)
            results[label] = res
            if args.diff_png and not res["byte_identical"]:
                save_diff(a, ref, Path(args.diff_png) / f"{label.replace('/', '-')}.png")
        except Exception as exc:                       # noqa: BLE001
            results[label] = {"error": f"{type(exc).__name__}: {exc}"}

    def summarise(items):
        ok = {k: v for k, v in items.items() if "error" not in v}
        diff = {k: v for k, v in ok.items() if not v["byte_identical"]}
        s = {"images": len(items), "errors": len(items) - len(ok), "identical": len(ok) - len(diff),
             "differing": len(diff)}
        if diff:
            s["max_abs_diff_overall"] = max(v["max_abs_diff"] for v in diff.values())
            s["median_max_abs_diff"] = float(np.median([v["max_abs_diff"] for v in diff.values()]))
            s["median_diff_pixels_pct"] = float(np.median([v["diff_pixels_pct"] for v in diff.values()]))
            s["max_diff_pixels_pct"] = max(v["diff_pixels_pct"] for v in diff.values())
            s["all_edge_only"] = all(v["edge_only"] for v in diff.values())
            s["edge_only_images"] = sum(v["edge_only"] for v in diff.values())
            s["differing_ids"] = sorted(diff)
            tot = {k: sum(v["histogram"][k] for v in diff.values()) for k, _, _ in BUCKETS}
            s["histogram_total"] = tot
        return s

    session = {k: v for k, v in results.items() if not k.startswith("gallery/")}
    gallery = {k: v for k, v in results.items() if k.startswith("gallery/")}
    doc = {"a": args.a, "reference": ref_name, "reference_kind": "rendered" if B is not None else "golden png",
           "summary": {"all": summarise(results), "session1": summarise(session), "gallery": summarise(gallery)},
           "missing_reference": missing, "images": results}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1), encoding="utf-8")

    print(f"A = {args.a}   reference = {ref_name}\n")
    print("| image | identical | diff px | % | max | mean | 1 | 2 | 3-4 | 5-8 | 9-16 | 17+ | edge share | edge-only | bbox |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for label, r in results.items():
        if "error" in r:
            print(f"| {label} | error: {r['error']} |")
            continue
        if r["byte_identical"]:
            print(f"| {label} | yes | 0 | 0 | 0 | 0 | | | | | | | | | |")
            continue
        h = r["histogram"]
        print(f"| {label} | no | {r['diff_pixels']} | {r['diff_pixels_pct']:.3f} | {r['max_abs_diff']} | "
              f"{r['mean_abs_diff']:.2f} | {h['1']} | {h['2']} | {h['3-4']} | {h['5-8']} | {h['9-16']} | {h['17+']} | "
              f"{r['share_in_edge_mask']:.3f} | {'yes' if r['edge_only'] else 'no'} | {r['bbox']} |")
    for name, s in doc["summary"].items():
        print(f"\n{name}: {s}")
    if missing:
        print("\nno reference for:", ", ".join(missing))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
