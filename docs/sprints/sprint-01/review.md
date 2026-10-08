# Sprint 01 review — spike S-134

**Date:** 8 October 2026. **Outcome:** the spike answered all four questions. Details and numbers are in
[RESULTS.md](../../../RESULTS.md).

## Done

| Story | Result | Evidence |
|---|---|---|
| S-134.1 Toolchain | emsdk 5.0.3, pyodide-build 0.39.1, xbuildenv 314.0.7 on host CPython 3.14, working around the blocked hosts | `scripts/setup_toolchain.sh`, README |
| S-134.2 wasm build | pycairo 1.29.2 wheel with static cairo 1.18.4, pixman 0.46.4, libpng, zlib; three small patches | `scripts/build_wasm.sh`, `patches/` |
| S-134.3 Native control and harness | native build from the same sources is byte-identical to all 91 goldens | `results/native/` |
| S-134.4 Pyodide in Node | Session 1: 13/13 identical; gallery 70/74 identical, 4 differences from JPEG decoding and pygame smoothscale, cairo verified clean, 4 need sound | `results/pyodide/` |
| S-134.5 Text | uharfbuzz from PyPI's wasm wheel; skia-pathops built (required by `import funground`) | `scripts/build_pathops_wasm.sh` |
| S-134.6 Frame time | Cairo replay at 1280×800: 16.5 ms mean in Node vs 7.8 native (2.0×); Python `draw()` dominates full frames | `results/bench_comparison.md` |
| S-134.7 Size | 1.65 MB for the three wheels | RESULTS.md (d) |
| S-134.8 CI | workflow green on GitHub in about 6 min, artifact `wheels` | `.github/workflows/build.yml` |
| S-134.9 Results | RESULTS.md, this review | |

## Criteria

(a) **pass** · (b) **pass** (Session 1) · (c) **fail as written** (Cairo 16.5 ms mean; Python is the larger
share) · (d) **pass**.

## What went well

- A three-way comparison (Windows goldens, native control, wasm) quickly ruled out the version and
  compiler gap: every difference left points at one cause.
- Running the native control and the wasm build in parallel saved most of a day.

## What didn't

- The sandbox blocked the usual hosts. We pinned alternative mirrors early, which cost about an hour.
- Bench numbers from the first native run were taken under build load. They were re-measured back to back
  with Node.
- `pygame.mixer` cannot start in Node, which hides 4 sound goldens behind a stub.

## Carried forward / new candidate stories (for funground's backlog)

- Maintainer decision on criterion (c) (RESULTS.md, "Decision needed").
- Time the same examples in Chrome on the teaching machine, including presenting the frame to a canvas (part of S-135/S-136).
- Rebuild with cairo 1.18.6 in CI (open network) to close ADR-002's version gap.
- JPEG decoding parity: a pure-PNG gallery photo, or tolerance for decoded images.
- Profile `draw()` in Pyodide for the heaviest sketches (text shaping, path ops): the larger share of frame time.
